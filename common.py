import re
import pandas as pd
import numpy as np


# all st element varaible with return value defined with prefix st_ in this code
# add 'SH' or 'SZ' as code prefix for east money data source
def add_prefix_to_code(code: str) -> str:
    code = code.strip()
    if code.startswith('6'):
        code = 'SH' + code
    if code.startswith(('0', '3')):
        code = 'SZ' + code
    return code

# 带亿等数字文本转纯数字 - 报表原始带单位数据转成纯数字
def str_to_num(value: str|float|int) -> float:
    match = re.match(r'([-+]?\d*\.?\d*)(亿|千万|百万|万|千)?', str(value).strip())
    if not match:
        return value
    if match.group(2) is None:  # 报告期会匹配到group(1)，这个条件防止报告期列执行后面语句
        return value
    num = float(match.group(1))
    unit = match.group(2)
    unit_map = {'亿': 100000000, '千万': 10000000, '百万': 1000000, '万': 10000, '千': 1000, None: 1}
    return num * unit_map[unit]

# 纯数字转带亿等单位数字文本 - 格式化plotly图表上显示的文本 
def num_to_str(value: float|int|str) -> str:
    # np.nan不处理，便于后续计算
    if pd.isna(value):
        return np.nan
    # if value is string or pd.Timestamp ('报告期'列为Timestamp), return directly
    if isinstance(value, (str, pd.Timestamp)):
        return value
    if value:
        if abs(value)>1e8:
            return f'{value/1e8:.2f}亿'
        # elif abs(value)>1e6:
        #     return f'{value/1e6:.2f}百万'
        elif abs(value)>10000:
            return f'{value/10000:.2f}万'
        else:
            return f'{value:.2f}'

# col_maps df.columns - ths, em, sina, item
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
        # ths 原始数据空值为False，把False用np.nan替代
        # df = df.replace(False, np.nan)
        df = df.mask(df==False, np.nan)
        # ths利润表 资产减值损失，信用减值损 的取值与em和sina是反的，用的话需要取反
        df = df.map(str_to_num)
    if(source=='sina'):
        # format number to float
        df = df.map(lambda v: float(v) if isinstance(v, (float, int)) else v)

    # df = df.map(num_to_str)   # 仅用于测试，格式化成数字更方面后续的计算
    return df

# return quarter report. df need to format as number, report_date_col_name need to format as pd.to_datetime
def get_quarter_report(df: pd.DataFrame, report_date_col_name: str) -> pd.DataFrame:
    df_number = df.select_dtypes(include=['float', 'int']) 
    # em, ths, sina的时间都是降序，所以用 diff(-1)。所有行都减后面一行的数据
    df_q = df_number.diff(-1, axis=0) 
    mask_Q1 = df[report_date_col_name].dt.month == 3
    df_q[mask_Q1] = df_number[mask_Q1]   # 得到Q1行mask，恢复Q1行的数据 
    
    df_q = pd.concat([df[report_date_col_name], df_q], axis=1)  # 把报告期列加到最前面
    return df_q
