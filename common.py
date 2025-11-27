import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# =======================   variable declaration  ======================================
# ======================================================================================
# data source used by akshare - 'shown on web': 'called by function'
# 代码中所有source都是按照这个定义的，web上显示的可以改动，代码调用的是固定的不要改动
DATA_SOURCE = {'ths': 'ths', 'east money': 'em', 'sina': 'sina'}
# BALANCE_BY_REPORT = 'balance_sheet_by_report'
# PROFIT_BY_REPORT = 'profit_sheet_by_report'
# PROFIT_BY_QUARTER = 'profit_sheet_by_quarter'
# CASH_BY_REPORT = 'cash_sheet_by_report'
# CASH_BY_QUARTER = 'cash_sheet_by_quarter'
BALANCE_BY_REPORT = '资产负债表-报告期'
PROFIT_BY_REPORT = '利润表-报告期'
CASH_BY_REPORT = '现金流量表-报告期'
PROFIT_BY_QUARTER = '利润表-单季度'
CASH_BY_QUARTER = '现金流量表-单季度'   
# 定义用来存储报告的变量 key-报表名字，value-报表数据pd.Dataframe。
# 报告期数据 reports reports_filtered (使用st.sidebar选项过滤后的数据)，单季度数据 reports_quarter reports_quarter_filtered 
# reports 使用多线程函数 get_all_reports_concurrently自动生成，这里不需要定义，只需要知道数据格式就行
# reports = {PROFIT_BY_REPORT: pd.DataFrame(), CASH_BY_REPORT: pd.DataFrame(), BALANCE_BY_REPORT: pd.DataFrame()}
reports_filtered = {PROFIT_BY_REPORT: pd.DataFrame(), CASH_BY_REPORT: pd.DataFrame(), BALANCE_BY_REPORT: pd.DataFrame()}
reports_quarter = {PROFIT_BY_QUARTER: pd.DataFrame(), CASH_BY_QUARTER: pd.DataFrame()}
reports_quarter_filtered = {PROFIT_BY_QUARTER: pd.DataFrame(), CASH_BY_QUARTER: pd.DataFrame()}

# const used to generate quarter and year columns for chart ploting
YEAR = '年份'
QUARTER = '季度'
# ======================================================================================
# ======================================================================================

# all st element varaible with return value defined with prefix st_ in this code
# add 'SH' or 'SZ' as code prefix for east money data source
# 用于em的akshare调用，ths和sina不需要
def add_prefix_to_code(code: str) -> str:
    code = code.strip()
    if code.startswith('6'):
        code = 'SH' + code
    if code.startswith(('0', '3')):
        code = 'SZ' + code
    return code
# try:
#             res = float(value)
#         except:
#             res = 'xxxx'
#         finally:
#             return res
# 带亿等数字文本转纯数字 
# 用于将ths的原始数据转成纯数字
def ths_str_to_num(value: str|float|int) -> float:
    match = re.match(r'^([-+]?\d*\.?\d*)(亿|千万|百万|万|千)?$', str(value).strip())
    if not match:  # 报告期无法匹配到，直接返回
        return value
    if match.group(2) is None:  # 只有1个捕获组的说明没有汉字单位，转成float
        # 避坑，可能会匹配到''空字符，使用float会出错，把空字符的情况要排除
        # pattern为了匹配 .5  2 这些数字，导致可能会匹配到空字符
        if str(value).strip() == '':
            return value
        else:
            return float(value)
    num = float(match.group(1))
    unit = match.group(2)
    unit_map = {'亿': 100000000, '千万': 10000000, '百万': 1000000, '万': 10000, '千': 1000}
    return num * unit_map[unit]

# 用于st web显示，把df所有值变成string，便于显示
def value_to_str(value: float|int|str) -> str:
    # np.nan使用'-'显示, np.na属于float，需要先处理。np.na和任何float比较都返回False
    if pd.isna(value):
        return '-'
    # 处理数字类型
    if isinstance(value, (int, float)):
        if abs(value)>1e8:
            return f'{value/1e8:.2f}亿'
        # elif abs(value)>1e6:
        #     return f'{value/1e6:.2f}百万'
        elif abs(value)>10000:
            return f'{value/10000:.1f}万'
        else:
            return f'{value: .2f}'
    # string, directly return
    if isinstance(value, (str)):
        return value
    # 格式化日期类型的报告期列
    if isinstance(value,  pd.Timestamp):
        value: pd.Timestamp
        return value.strftime('%Y-%m-%d')
    
    # 其余类型，使用str函数转换
    return str(value)

# col_maps df.columns - ths, em, sina, item
# 按照col_maps重命名列名，列进行排序，'报告期'列转成pd.to_datetime。
# 把数字都转成float，方便后续的相关计算。np.na 保持不变，np.na实际可能是没有值，也可能是代表0。
# 保持np.na不变会导致计算单季度数据时出现问题，np.na参与计算时结果变成np.na，可能与实际不符，不过影响很小，可以先不用管
def format_report(df: pd.DataFrame, df_col_maps: pd.DataFrame, source: str='em'):    
    #根据source值赋值col_maps, key为source列，value为item列
    col_maps = df_col_maps.set_index(source)['item'].to_dict()
    # col_maps = dict(zip(df_col_maps[source], df_col_maps['item']))
    #按col_maps,重命名报表的列名，形成统一的报表列名
    df = df.rename(columns={k:v for k, v in col_maps.items() if k !=None and k in df.columns})
    # 只取col_maps中存在的列(用col_maps.values()内容排序)，其余列可加上或过滤掉
    col_orders = [c for c in col_maps.values() if c in df.columns] + [c for c in df.columns if c not in col_maps.values()]
    df = df[col_orders]
    # '报告期'列格式化成datetime，后面不能加.dt.strftime('%Y-%m-%d')，否则会变成str类型，不能再调用dt函数
    df['报告期'] = pd.to_datetime(df['报告期'], errors='coerce')

    # remove east money YOY lines
    if(source=='em'):
        df = df[[col for col in df.columns if not col.endswith('YOY')]]
        # format number to float
        df = df.map(lambda v: float(v) if isinstance(v, (float, int)) else v)
    # convet ths data to number
    if(source=='ths'):
        # ths 原始数据空值为False，把False用np.nan替代。replace和mask都可以实现
        # df = df.replace(False, np.nan)
        df = df.mask(df==False, np.nan)
        # ths 原始数据包含亿和万等中文字符，需要用函数str_to_num转成纯数字
        # ths利润表 资产减值损失，信用减值损 的取值与em和sina是反的，用的话需要取反
        df = df.map(ths_str_to_num)
    if(source=='sina'):
        # format number to float
        df = df.map(lambda v: float(v) if isinstance(v, (float, int)) else v)

    # df = df.replace(np.nan, 0) # 把np.na赋值成0，仅用于对比测试
    # df = df.map(value_to_str)   # 仅用于显示测试
    return df

# return quarter report. df need to format as number, report_date_col_name need to format as pd.to_datetime
# 由于sina没有单季度报告的数据供抓取，这里都自行进行计算
def get_quarter_report(df: pd.DataFrame, report_date_col_name: str) -> pd.DataFrame:
    df_number = df.select_dtypes(include=['float', 'int']).copy()
    # em, ths, sina的时间都是降序，所以用 diff(-1)，axis=0按行处理。所有行都减后面一行的数据。如果原始数据顺序改变，代码要修改
    df_q = df_number.diff(-1, axis=0) 
    # 第一季度数据不需要向下减，mask_Q1筛选出第一季度的数据，把数据还原回来
    mask_Q1 = df[report_date_col_name].dt.month == 3
    df_q[mask_Q1] = df_number[mask_Q1]   # 得到Q1行mask，恢复Q1行的数据 
    
    df_q = pd.concat([df[report_date_col_name], df_q], axis=1)  # 把报告期列加到最前面
    return df_q

def safe_yoy(series, periods=4):
    """
    计算同比增长，安全处理零和负数。
    
    series: pd.Series，数值列
    periods: int, 同比的周期（如季度同比用4）
    """
    prev = series.shift(periods)
    
    def calc(current, previous):
        if previous == 0:
            return np.nan  # 避免除零
        return (current - previous) / abs(previous) * 100  # 用 abs 保证同比符号合理
    
    return pd.Series([calc(c, p) for c, p in zip(series, prev)], index=series.index)


# plot bar chart grouped by quarter. x is year, y is col data. fig1 is col data, fig2 is data of col.pct_change(-4)
def plot_bar_quarter_group_px(df: pd.DataFrame, col: str):
    col_pct = col+'_同比'
    #df[col_pct] = df[col].pct_change(-4)*100
    df[col_pct] = safe_yoy(df[col], periods=-4)
    fig1 = px.bar(df, x=YEAR, y=col, color=QUARTER, barmode='group', height =300,
                text=df[col].map(value_to_str), category_orders={QUARTER: ['Q1', 'Q2', 'Q3', 'Q4']})
    fig1.update_layout(barmode='group', bargap=0.15,
        legend=dict(
            orientation="h",      # 水平放置
            yanchor="bottom",     # legend 底部对准 y=1
            y=1,                # 往上移（>1 代表在绘图区上方）
            xanchor="left",
            x=0),
        # 可选：调整图表整体字体大小（统一风格）
        font=dict(size=12))
    # 核心修改：调大柱子文字大小 + 优化文字位置
    fig1.update_traces(
        textfont_size=20,  # 文字大小（默认约10，根据需求调整，如12/14/16）
        textposition='inside',  # 文字放在柱子外部（避免内部拥挤）
        textangle=90,  # 文字水平显示（原默认可能倾斜，更易读）
        insidetextanchor='end'  # 若后续改为内部显示，文字居中 [start, end, middle, left, right]
    )
    fig1.update_xaxes(showgrid=True)
    # fig1.update_yaxes(showgrid=True)

    # df_pct = df.dropna()
    fig2 = px.bar(df, x=YEAR, y=col_pct, color=QUARTER, barmode='group', height =300,
                text=df[col_pct].map(value_to_str), category_orders={QUARTER: ['Q1', 'Q2', 'Q3', 'Q4']})
    fig2.update_layout(barmode='group', bargap=0.15,
        legend=dict(
            orientation="h",      # 水平放置
            yanchor="bottom",     # legend 底部对准 y=1
            y=1,                # 往上移（>1 代表在绘图区上方）
            xanchor="left",
            x=0))
    # 核心修改：调大柱子文字大小 + 优化文字位置
    fig2.update_traces(
        textfont_size=20,  # 文字大小（默认约10，根据需求调整，如12/14/16）
        textposition='inside',  # 文字放在柱子外部（避免内部拥挤）
        textangle=90,  # 文字水平显示（原默认可能倾斜，更易读）
        insidetextanchor='end'  # 若后续改为内部显示，文字居中 [start, end, middle, left, right]
    )
    fig2.update_xaxes(showgrid=True)

    return fig1, fig2

def plot_bar_quarter_group_plt(df: pd.DataFrame, col: str):
    # 格式化图表上要显示的值
    def val_formatter(val):
        if val==0:
            return ''
        if abs(val) >= 1e8:
            return f"{val/1e8:.2f}亿"
        elif abs(val) >= 1e4:
            return f"{val/1e4:.1f}万"
        else:
            return f"{val:.2f}"
    col_pct = col+'_同比'
    df[col_pct] = df[col].pct_change(-4)*100
    fig1, ax1 = plt.subplots(figsize=(10, 3))
    pv1 = df.pivot(index=YEAR, columns=QUARTER, values=col)
    pv1.plot.bar(ax=ax1, width=0.85)  # width 可调整bar的宽度和间距
    ax1.set_title(col)
    # Y 轴刻度格式化（关键）
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: val_formatter(v)))
    # 在柱子内添加竖排文字
    for p in ax1.patches:
        value = p.get_height()
        # ha 水平对齐，va 垂直对齐
        ax1.annotate(f"{val_formatter(value)}",
                     (p.get_x() + p.get_width() / 2, p.get_height()),
                     ha='center', va='top', fontsize=11, rotation=90, fontweight='bold')
    ax1.grid(axis='both', linestyle='--', alpha=0.5)

    # ====================  fig2 ===========================
    fig2, ax2 = plt.subplots(figsize=(10, 3))
    df.pivot(index=YEAR, columns=QUARTER, values=col_pct).plot.bar(ax=ax2)
    ax2.set_title(col_pct)
    # Y 轴刻度格式化（关键）
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: val_formatter(v)))
    # 在柱子内添加竖排文字
    for p in ax2.patches:
        value = p.get_height()
        # ha 水平对齐，va 垂直对齐
        ax2.annotate(f"{val_formatter(value)}",
                     (p.get_x() + p.get_width() / 2, p.get_height()),
                     ha='center', va='top', fontsize=11, rotation=90, fontweight='bold')
    ax2.grid(axis='both', linestyle='--', alpha=0.5)

    return fig1, fig2





    






