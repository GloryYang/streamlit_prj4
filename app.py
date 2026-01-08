import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import streamlit as st

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# =======================   variable declaration  ======================================
# ======================================================================================
# data source used by akshare - 'shown on web': 'called by function'
# 代码中所有source都是按照这个定义的，web上显示的可以改动，代码调用的是固定的不要改动
DATA_SOURCE = {'ths': 'ths', 'east money': 'em', 'sina': 'sina'}
CROSS_REPORT = '综合分析'
PROFIT_BY_REPORT = '利润表-报告期'
CASH_BY_REPORT = '现金流量表-报告期'
BALANCE_BY_REPORT = '资产负债表-报告期'

PROFIT_BY_QUARTER = '利润表-单季度'
CASH_BY_QUARTER = '现金流量表-单季度'

PROFIT_PCT_BY_REPORT = '利润表-报告期同比'
PROFIT_PCT_BY_QUARTER = '利润表-单季度同比'
CASH_PCT_BY_REPORT = '现金流量表-报告期同比'
CASH_PCT_BY_QUARTER = '现金流量表-单季度同比'
BALANCE_PCT_BY_REPORT = '资产负债表-报告期同比'


# PROFIT = '利润表'
# CASH = '现金流量表'
# BALANCE = '资产负债表'
# 定义用来存储报告的变量 key-报表名字，value-报表数据pd.Dataframe。
# 报告期数据 reports reports_filtered (使用st.sidebar选项过滤后的数据)，单季度数据 reports_quarter reports_quarter_filtered 
# reports 使用多线程函数 get_all_reports_concurrently自动生成，这里不需要定义，只需要知道数据格式就行
reports = {CROSS_REPORT: pd.DataFrame(),
           PROFIT_BY_REPORT: pd.DataFrame(),       # 经过格式化的原始数据
           CASH_BY_REPORT: pd.DataFrame(),         # 经过格式化的原始数据
           BALANCE_BY_REPORT: pd.DataFrame(),      # 经过格式化的原始数据

           PROFIT_BY_QUARTER: pd.DataFrame(),      #计算得到的单季度数据
           CASH_BY_QUARTER: pd.DataFrame(),        #计算得到的单季度数据

           PROFIT_PCT_BY_REPORT: pd.DataFrame(),   #计算得到利润表报告期同比数据
           PROFIT_PCT_BY_QUARTER: pd.DataFrame(),  #计算得到利润表单季度同比数据
           CASH_PCT_BY_REPORT: pd.DataFrame(),     #计算得到现金流量表报告期同比数据
           CASH_PCT_BY_QUARTER: pd.DataFrame(),    #计算得到现金流量表单季度同比数据
           BALANCE_PCT_BY_REPORT: pd.DataFrame(),  #计算得到资产负债表报告期同比数据
           }
# 经过sidebar选项筛选的报表数据，用于可视化显示
reports_filtered = {CROSS_REPORT: pd.DataFrame(),
                    PROFIT_BY_REPORT: pd.DataFrame(),       # 经过格式化的原始数据
                    CASH_BY_REPORT: pd.DataFrame(),         # 经过格式化的原始数据
                    BALANCE_BY_REPORT: pd.DataFrame(),      # 经过格式化的原始数据

                    PROFIT_BY_QUARTER: pd.DataFrame(),      #计算得到的单季度数据
                    CASH_BY_QUARTER: pd.DataFrame(),        #计算得到的单季度数据

                    PROFIT_PCT_BY_REPORT: pd.DataFrame(),   #计算得到利润表报告期同比数据
                    PROFIT_PCT_BY_QUARTER: pd.DataFrame(),  #计算得到利润表单季度同比数据
                    CASH_PCT_BY_REPORT: pd.DataFrame(),     #计算得到现金流量表报告期同比数据
                    CASH_PCT_BY_QUARTER: pd.DataFrame(),    #计算得到现金流量表单季度同比数据
                    BALANCE_PCT_BY_REPORT: pd.DataFrame(),  #计算得到资产负债表报告期同比数据
                    }

# const used to generate quarter and year columns for chart ploting
YEAR = '年份'
QUARTER = '季度'
REPORT_DATE = '报告期'
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
    match = re.match(r'^([-+]?\d*\.?\d*)(万亿|亿|千万|百万|万|千)?$', str(value).strip())
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
    unit_map = {'万亿':1000000000000, '亿': 100000000, '千万': 10000000, '百万': 1000000, '万': 10000, '千': 1000}
    return num * unit_map[unit]

# 用于st web显示，把df所有值变成string，便于显示
def value_to_str(value: float|int|str) -> str:
    # np.nan使用'-'显示, np.na属于float，需要先处理。np.na和任何float比较都返回False
    if pd.isna(value):
        return '-'
    # 处理数字类型
    if isinstance(value, (int, float)):
        if abs(value)>1e12:
            return f'{value/1e12:.2f}万亿'
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
    ### 按col_maps,重命名报表的列名，形成统一的报表列名
    df = df.rename(columns={k:v for k, v in col_maps.items() if k !=None and k in df.columns})
    # 只取col_maps中存在的列(用col_maps.values()内容排序)，其余列可加上或过滤掉
    col_orders = [c for c in col_maps.values() if c in df.columns] + [c for c in df.columns if c not in col_maps.values()]
    df = df[col_orders]
    ### '报告期'列格式化成datetime，后面不能加.dt.strftime('%Y-%m-%d')，否则会变成str类型，不能再调用dt函数
    df[REPORT_DATE] = pd.to_datetime(df[REPORT_DATE], errors='coerce')

    ### em数据转换，remove east money YOY lines,
    if(source=='em'):
        df = df[[col for col in df.columns if not col.endswith('YOY')]]
        # format number to float
        df = df.map(lambda v: float(v) if isinstance(v, (float, int)) else v)
    ### ths数据处理，convet ths data to number
    if(source=='ths'):
        # ths 原始数据空值为False，把False用np.nan替代。replace和mask都可以实现
        # df = df.replace(False, np.nan)
        df = df.mask(df==False, np.nan)
        # ths 原始数据包含亿和万等中文字符，需要用函数ths_str_to_num转成纯数字
        # ths利润表 资产减值损失，信用减值损 的取值与em和sina是反的，用的话需要取反，这里暂时没处理
        df = df.map(ths_str_to_num)
    ### sina数据处理
    if(source=='sina'):
        # format number to float
        df = df.map(lambda v: float(v) if isinstance(v, (float, int)) else v)

    # df = df.replace(np.nan, 0) # 把np.na赋值成0，仅用于对比测试
    # df = df.map(value_to_str)   # 仅用于显示测试
    return df

# return quarter report. df need to format as number, report_date_col_name need to format as pd.to_datetime
# 由于sina没有单季度报告的数据供抓取，这里都自行进行计算
# 注意：某些数据为na的话，计算结果也会na，有些单季度计算出来的数据可能会不准
def get_quarter_report(df: pd.DataFrame, report_date_col_name: str) -> pd.DataFrame:
    df_number = df.select_dtypes(include=['float', 'int']).copy()
    # em, ths, sina的时间都是降序，所以用 diff(-1)，axis=0按行处理。所有行都减后面一行的数据。如果原始数据顺序改变，代码要修改
    df_q = df_number.diff(-1, axis=0) 
    # 第一季度数据不需要向下减，mask_Q1筛选出第一季度的数据，把数据还原回来
    mask_Q1 = df[report_date_col_name].dt.month == 3
    df_q[mask_Q1] = df_number[mask_Q1]   # 得到Q1行mask，恢复Q1行的数据 
    
    df_q = pd.concat([df[report_date_col_name], df_q], axis=1)  # 把报告期列加到最前面
    return df_q

def safe_yoy(series: pd.Series, periods: int =-4) -> pd.Series:
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


def plot_bar_quarter_go(df: pd.DataFrame, col: str, title_suffix: str = '', height: int = 300) -> go.Figure:
    """
    plot bar quarter with group mode

    :param df: df need to be ploted. col is used as y data, x data is got from year of REPORT_DATE.
    :param col: con in df for y data
    :param title_suffix: col column name is used as title, title_sufifx is used as suffix if it's not ''.
    :param height: height of the chart
    """
    df = df.copy()
    df[QUARTER] = df[REPORT_DATE].dt.quarter.map(lambda x: f'Q{x}')
    df[YEAR] = df[REPORT_DATE].dt.year
    ### 根据col的数值大小计算文本显示在柱体外部的阈值, 阈值按照最大值的abs来设置
    threshold = df[col].abs().max() * 0.3
    df["textpos"] = df[col].apply(lambda val: 'inside' if abs(val)>threshold else 'outside')
    ### 定义颜色映射（可自定义）
    color_map = {'Q1':"#00CC41",'Q2':"#F86C53",'Q3':"#FAC363",'Q4':"#8B92F7"}
    ### 画出bar图并进行显示设置
    fig1 = go.Figure()
    # 分组绘制每个季度
    for quarter in ['Q1','Q2','Q3','Q4']:
        df_q = df[df[QUARTER] == quarter]
        fig1.add_trace(go.Bar(
            x=df_q[YEAR],
            y=df_q[col],
            name=quarter,
            text=df_q[col].map(value_to_str),  # 可以用 value_to_str 替代
            # textposition='inside',      # 一直 inside
            # insidetextanchor='middle',
            cliponaxis=False,           # 不裁剪文字
            marker_color=color_map[quarter]
        ))
    # fig1 = px.bar(df, x=YEAR, y=col, color=QUARTER, barmode='group', height=height,
    #             text=df[col].map(value_to_str), category_orders={QUARTER: ['Q1', 'Q2', 'Q3', 'Q4']})
    fig1.update_layout(barmode='group', bargap=0.15,
        height = height,
        # 设置legend
        legend=dict(
            x=0,
            y=1,                # 往上移（>1 代表在绘图区上方）
            orientation="h",      # 水平放置
            yanchor="bottom",     # legend 底部对准 y=1
            xanchor="left",
            ),
        # 设置图表title
        title=dict(
            text=f'{col} - {title_suffix}' if title_suffix else col,      # 用 ytitle 当作图表标题
            x=0.5,           # x=0.5居中, x=1 最右侧
            xanchor='center',
            yanchor='top',
            font=dict(size=12)),
        # 不显示x和y轴title
        yaxis_title=None,
        xaxis_title=None,
        uniformtext_minsize=11,     # 字体最小不能低于 12
        uniformtext_mode='show',     # 强制显示，不自动缩放
        # hovermode="x unified"      # 打开后在手机上的hover内容一直存在会遮挡数据，效果不太好
        )
    ### 设置bar上文本的位置，根据阈值计算的结果，按照trace来设置每个柱子文本显示的位置
    for i, quarter in enumerate(['Q1', 'Q2', 'Q3', 'Q4']):
        mask = df[QUARTER] == quarter
        fig1.data[i].textposition = df.loc[mask, "textpos"]
    # Plotly 在 group bars（分组柱状图）里，会把同一年份多个季度的柱子拆成多条 trace。
    fig1.update_traces(
        textfont_size=12,  # 文字大小（默认约10，根据需求调整，如12/14/16）
        # textposition='inside',  # 文字放在柱子外部（避免内部拥挤），根据threashold来设置
        textangle=90,  # 文字水平显示（原默认可能倾斜，更易读）
        insidetextanchor='end',  # 若后续改为内部显示，文字居中 [start, end, middle, left, right]
        # 设置hover template
        hovertemplate = '%{x}<br>%{fullData.name}: %{text}<extra></extra>'
    )
    fig1.update_xaxes(showgrid=True)
    # fig1.update_yaxes(showgrid=True)
    return fig1



# plot bar chart grouped by quarter. x is year, y is col data. fig1 is col data, fig2 is data of col.pct_change(-4)
def plot_bar_quarter_with_pct_go(df: pd.DataFrame, col: str, height: int = 300):
    ### 计算同比数据
    col_pct = col+'_同比'
    #df[col_pct] = df[col].pct_change(-4)*100
    df[col_pct] = safe_yoy(df[col], periods=-4)

    fig1 = plot_bar_quarter_go(df, col, height)
    fig2 = plot_bar_quarter_go(df, col_pct, height)
    return fig1, fig2

# 画资产负债表饼图
# col_maps_dict 报表映射df字典，df_balance [资产负债表-报告期]
def plot_pie_balance(col_maps_dict, df_balance: pd.DataFrame, height):
    cols_date = df_balance[REPORT_DATE].dt.strftime('%Y-%m').to_list()
    st_date = st.selectbox('选择资产负债表饼图日期：', options=cols_date)
    date_index = cols_date.index(st_date)

    fig = make_subplots(rows=1, cols=2,
        specs=[[{"type": "domain"}, {"type": "domain"}]],
        subplot_titles=("资产", "负债"))
    ### 资产项
    df_col_map = col_maps_dict[BALANCE_BY_REPORT]
    cols_asset = df_col_map[(df_col_map['item_group']=='流动资产') | (df_col_map['item_group']=='非流动资产')]['item']
    cols_asset = [REPORT_DATE] + cols_asset.tolist()
    df = df_balance[[col for col in cols_asset if col in df_balance.columns]]
    # st.write(df)
    colors = px.colors.qualitative.Set3
    fig1 = go.Figure()
    fig1.add_trace(go.Pie(labels=df.columns[1:], values=df.iloc[date_index,1:], text=df.iloc[date_index,1:].map(value_to_str),
            textinfo="label+percent+text",
            textposition="inside",   # 关键 "auto" "outside"
            rotation=0,
            sort=False,
            outsidetextfont=dict(size=10),
            insidetextfont=dict(size=14),
            marker=dict(colors=colors),
            hovertemplate=
                "<b>%{label}</b><br>" +
                "金额：%{text}<br>" +
                "占比：%{percent:.2%}" +
                "<extra></extra>"),
                # row=1, col=1
                )
    fig1.update_layout(#legend=dict(x=0.9, y=0, bgcolor="rgba(255,255,255,0.6)"),
                        margin=dict(l=0, r=0, t=50, b=0, autoexpand=True), height=height)
    fig1.update_layout(showlegend=False)
    
    ### 负债项
    cols_liab = df_col_map[(df_col_map['item_group']=='流动负债') | (df_col_map['item_group']=='非流动负债')]['item']
    cols_liab = [REPORT_DATE] + cols_liab.tolist()
    df = df_balance[[col for col in cols_liab if col in df_balance.columns]]
    # st.write(df)
    colors = px.colors.qualitative.Set3
    fig2 = go.Figure()
    fig2.add_trace(go.Pie(labels=df.columns[1:], values=df.iloc[date_index,1:], text=df.iloc[date_index,1:].map(value_to_str),
            textinfo="label+percent+text",
            textposition="inside",   # 关键 "auto" "outside"
            rotation=0,
            sort=False,
            outsidetextfont=dict(size=10),
            insidetextfont=dict(size=14),
            marker=dict(colors=colors),
            hovertemplate=
                "<b>%{label}</b><br>" +
                "金额：%{text}<br>" +
                "占比：%{percent:.2%}" +
                "<extra></extra>"),
                # row=1, col=2
                )
    ### 设置显示效果
    fig2.update_layout(#legend=dict(x=0.9, y=0, bgcolor="rgba(255,255,255,0.6)"),
                        margin=dict(l=0, r=0, t=50, b=0, autoexpand=True), height=height)
    fig2.update_layout(showlegend=False)
    return fig1, fig2

'''
# px柱体上文字显示的效果不是很好，文字显示到画布以外就看不到了
# plot bar chart grouped by quarter. x is year, y is col data. fig1 is col data, fig2 is data of col.pct_change(-4)
def plot_bar_quarter_with_pct_px(df: pd.DataFrame, col: str, height: int = 300):
    ### 计算同比数据
    col_pct = col+'_同比'
    #df[col_pct] = df[col].pct_change(-4)*100
    df[col_pct] = safe_yoy(df[col], periods=-4)

    ### 根据col的数值大小计算文本显示在柱体外部的阈值, 阈值按照最大值的abs来设置
    threshold = df[col].abs().max() * 0.3
    df["textpos"] = df[col].apply(lambda val: 'inside' if abs(val)>threshold else 'outside')
    ### 画出bar图并进行显示设置
    fig1 = px.bar(df, x=YEAR, y=col, color=QUARTER, barmode='group', height=height,
                text=df[col].map(value_to_str), category_orders={QUARTER: ['Q1', 'Q2', 'Q3', 'Q4']})
    fig1.update_layout(barmode='group', bargap=0.15,
        # 设置legend
        legend=dict(
            x=0,
            y=1,                # 往上移（>1 代表在绘图区上方）
            orientation="h",      # 水平放置
            yanchor="bottom",     # legend 底部对准 y=1
            xanchor="left",
            ),
        # 设置图表title
        title=dict(
            text=col,      # 用 ytitle 当作图表标题
            x=1,           # x=0.5居中, x=1 最右侧
            xanchor='right',
            yanchor='top',
            font=dict(size=12)),
        # 不显示x和y轴title
        yaxis_title=None,
        xaxis_title=None,
        uniformtext_minsize=12,     # 字体最小不能低于 12
        uniformtext_mode='show'     # 强制显示，不自动缩放
        )
    ### 根据阈值计算的结果，按照trace来设置每个柱子文本显示的位置
    # 按 trace（季度）赋值
    for i, quarter in enumerate(['Q1', 'Q2', 'Q3', 'Q4']):
        mask = df[QUARTER] == quarter
        fig1.data[i].textposition = df.loc[mask, "textpos"]
    # Plotly 在 group bars（分组柱状图）里，会把同一年份多个季度的柱子拆成多条 trace。
    fig1.update_traces(
        textfont_size=12,  # 文字大小（默认约10，根据需求调整，如12/14/16）
        #textposition='inside',  # 文字放在柱子外部（避免内部拥挤）
        textangle=90,  # 文字水平显示（原默认可能倾斜，更易读）
        insidetextanchor='end'  # 若后续改为内部显示，文字居中 [start, end, middle, left, right]
    )
    fig1.update_xaxes(showgrid=True)
    # fig1.update_yaxes(showgrid=True)


    ### 根据col的数值大小计算文本显示在柱体外部的阈值, 阈值按照最大值的abs来设置
    threshold = df[col_pct].abs().max() * 0.3
    df["textpos"] = df[col_pct].apply(lambda val: 'inside' if abs(val) > threshold else 'outside')
    ### 画出bar图并进行显示设置
    fig2 = px.bar(df, x=YEAR, y=col_pct, color=QUARTER, barmode='group', height=height,
                text=df[col_pct].map(value_to_str), category_orders={QUARTER: ['Q1', 'Q2', 'Q3', 'Q4']})
    fig2.update_layout(barmode='group', bargap=0.15,
         # 设置legend
        legend=dict(
            x=0,
            y=1,                # 往上移（>1 代表在绘图区上方）
            orientation="h",      # 水平放置
            yanchor="bottom",     # legend 底部对准 y=1
            xanchor="left",
            ),
        # 设置图表title
        title=dict(
            text=col_pct,      # 用 ytitle 当作图表标题
            x=1,           # x=0.5居中, x=1 最右侧
            xanchor='right',
            yanchor='top',
            font=dict(size=12)),
        # 不显示x和y轴title
        yaxis_title=None,
        xaxis_title=None,
        uniformtext_minsize=12,     # 字体最小不能低于 12
        uniformtext_mode='show'     # 强制显示，不自动缩放
        )
    ### 根据阈值计算的结果，按照trace来设置每个柱子文本显示的位置
    # 按 trace（季度）赋值
    for i, quarter in enumerate(['Q1', 'Q2', 'Q3', 'Q4']):
        mask = df[QUARTER] == quarter
        fig2.data[i].textposition = df.loc[mask, "textpos"]
    fig2.update_traces(
        textfont_size=12,  # 文字大小（默认约10，根据需求调整，如12/14/16）
        # textposition=df["textpos"],  # 文字放在柱子外部（避免内部拥挤）
        textangle=90,  # 文字水平显示（原默认可能倾斜，更易读）
        insidetextanchor='end'  # 若后续改为内部显示，文字居中 [start, end, middle, left, right]
    )
    fig2.update_xaxes(showgrid=True)
    return fig1, fig2

def plot_bar_quarter_with_pct_plt(df: pd.DataFrame, col: str):
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
'''




    
