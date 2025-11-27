import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed
import time, os, re

from common import *


@st.cache_data
def get_stock_list() -> pd.DataFrame:
    df=pd.read_csv(r'stock_list1.csv', header=0)
    return df
@st.cache_data
# col_maps_dict {report_name: df in sheet_name}
def get_col_maps_dict() -> dict[str, pd.DataFrame]:
    sheet_map = {PROFIT_BY_REPORT: 'profit',
                 BALANCE_BY_REPORT: 'balance',
                 CASH_BY_REPORT: 'cash'}
    # sheets_df {sheet_name: df, ...}
    sheets_df = pd.read_excel(r'col_maps.xlsx', sheet_name=list(sheet_map.values()), header=0)
    col_maps_dict = {k: sheets_df[v] for k, v in sheet_map.items()}
    return col_maps_dict

# 资产负债表 - 报告期
@st.cache_data(ttl=3600, show_spinner=False)
def get_balance_sheet_by_report(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_debt_ths(symbol=code, indicator="按报告期")
    elif source == 'em':
        return ak.stock_balance_sheet_by_report_em(symbol=add_prefix_to_code(code))
    elif source == 'sina':
        return ak.stock_financial_report_sina(stock=code, symbol="资产负债表")
    else:
        return pd.DataFrame()
# 利润表 - 报告期和季度, sina 没有提供按季度的报表
@st.cache_data(ttl=3600, show_spinner=False)
def get_profit_sheet_by_report(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_benefit_ths(symbol=code, indicator="按报告期")
    elif source == 'em':
        return ak.stock_profit_sheet_by_report_em(symbol=add_prefix_to_code(code))
    elif source == 'sina':
        return ak.stock_financial_report_sina(stock=code, symbol="利润表")
    else:
        return pd.DataFrame()
@st.cache_data(ttl=3600, show_spinner=False)
def get_profit_sheet_by_quarterly(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_benefit_ths(symbol=code, indicator="按单季度")
    elif source == 'em':
        return ak.stock_profit_sheet_by_quarterly_em(symbol=add_prefix_to_code(code))
    else:
        return pd.DataFrame()
# 现金流量表 - 报告期和季度, sina 没有提供按季度的报表
@st.cache_data(ttl=3600, show_spinner=False)
def get_cash_sheet_by_report(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_cash_ths(symbol=code, indicator="按报告期")
    elif source == 'em':
        return ak.stock_cash_flow_sheet_by_report_em(symbol=add_prefix_to_code(code))
    elif source == 'sina':
        return ak.stock_financial_report_sina(stock=code, symbol="现金流量表")
    else:
        return pd.DataFrame()
@st.cache_data(ttl=3600, show_spinner=False)
def get_cash_sheet_by_quarterly(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_cash_ths(symbol=code, indicator="按单季度")
    elif source == 'em':
        return ak.stock_cash_flow_sheet_by_quarterly_em(symbol=add_prefix_to_code(code))
    else:
        return pd.DataFrame()
    
# thread function to get report
def get_all_reports_concurrently(code: str, source: str = 'ths') -> dict[str, pd.DataFrame]:
    # five reports as 
    tasks = [(PROFIT_BY_REPORT, get_profit_sheet_by_report, (code, source)),
             (CASH_BY_REPORT,get_cash_sheet_by_report, (code, source)),
             (BALANCE_BY_REPORT, get_balance_sheet_by_report, (code, source))]
            # 单季度数据后面自行计算，不从网上抓取了
            #  (PROFIT_BY_QUARTER, get_profit_sheet_by_quarterly, (code, source)),
            #  (CASH_BY_QUARTER, get_cash_sheet_by_quarterly, (code, source))

    results= {}
    futures_to_tasks = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            for name, func, args in tasks:
                futures_to_tasks[executor.submit(func, *args)] = (name,func.__name__, *args)
            # futures_to_tasks = {executor.submit(func, *args): name for name, func, args in tasks}

    
    for future in as_completed(futures_to_tasks.keys()):
        report_name, func_name, code, source = futures_to_tasks[future]
        try:
            # st.write(report_name, func_name, code, source )
            results[report_name] = future.result()
        except Exception as e:
            # 捕获异常，返回空 DataFrame
            st.error(f"❌ {report_name}下载失败，参数 （{code}，{source}）。错误代码：{str(e)}")
            results[report_name] = pd.DataFrame()
    
    # sort reports in results, 按照代码定义区的定义返回reports
    results = {report_name: results[report_name] for report_name, _, _ in tasks}
    return results



st.set_page_config(page_title="📈Finicial Report", layout="wide")
st.title("📈Finiacal Reprot Analysis")

with st.sidebar:
    st_data_source = st.selectbox('select data source:', ['ths', 'east money', 'sina'], 0)
    # st_slide_years = st.slider()
    # st_sheet_type = st.selectbox('select sheet type')

# =========================== stock list filter ================================================
# get stock list df and df_col_maps
df_stock_list = get_stock_list()
col_maps_dict = get_col_maps_dict()
df_stock_list['code'] = df_stock_list["code"].astype(str).str.zfill(6)

st_stock_code = st.text_input("ℹ️Please input stock code, name or initial (eg: 300416 or 汤臣倍健 or tcbj):")

# variable declaration under if statement for future use
df_stock_list_filterd = pd.DataFrame()
stock_selected_row = None 

# filter df_stock_list with input as filter condition
st_stock_code = st_stock_code.strip()
if st_stock_code:
    # filter df with input
    # df_stock_list_filterd = df_stock_list[(df_stock_list['code'].str.contains(st_stock_code, regex=False)) | 
    #                 df_stock_list['name'].str.contains(st_stock_code, regex=False) | df_stock_list['initial'].str.contains(st_stock_code.upper(), regex=False)]
    query_filter_expr = (
        "code.str.contains(@st_stock_code, regex=False, na=False) "  # don't match na
        "or name.str.contains(@st_stock_code, regex=False, na=False) "
        "or initial.str.contains(@st_stock_code.upper(), regex=False, na=False)"
    )
    df_stock_list_filterd = df_stock_list.query(query_filter_expr, engine='python')
    df_stock_list_filterd.reset_index(drop=True, inplace=True)
    df_stock_list_filterd.index += 1

    # show df_stock_list_filterd if not empty else show "no stock found"
    if not df_stock_list_filterd.empty:
        st.success(f"✅  {len(df_stock_list_filterd)} stock codes found as bellow:")
        st_stock_selected = st.dataframe(df_stock_list_filterd, width="stretch", 
                     height=(len(df_stock_list_filterd)+1)*35 if len(df_stock_list_filterd)<5 else 5*35,
                     selection_mode=['single-row'], on_select='rerun') 
        if len(st_stock_selected["selection"]["rows"])>0:
            # stock_selected format - {"selection":{"rows":[0:1]"columns":[]"cells":[]}}
            stock_selected_row = st_stock_selected["selection"]["rows"][0]
    else:
        st.error('❌  no stock code found')
st.markdown("---")
# ========================================================================

if stock_selected_row is None:
    st.stop()  # don't enter bellow codes if stock is not selected
else:
    stock_code = df_stock_list_filterd.iloc[stock_selected_row, 0]
    stock_name = df_stock_list_filterd.iloc[stock_selected_row, 1] 
    
st.subheader(f'📊 {stock_name}({stock_code}) 财务报表分析 - {st_data_source}') # get stock code by stock_selected_row


with st.spinner("⏳ 正在下载数据，请稍候..."):
    # stock_balance_sheet_by_report = get_balance_sheet_by_report(stock_code, DATA_SOURCE[st_data_source])
    reports = get_all_reports_concurrently(stock_code, DATA_SOURCE[st_data_source])
st.success("✅ 数据下载完成！")

# 先格式化来自(ths, em, sina)的财务报表，统一格式，方便后续进行操作
for report_name, df in reports.items():
    reports[report_name] = format_report(df, df_col_maps=col_maps_dict[report_name], source=DATA_SOURCE[st_data_source])

# 设置年份过滤
with st.sidebar:
    # 找到所有 df 的最小和最大年份
    all_years = pd.concat([df['报告期'] for df in reports.values()])
    # all_years = pd.to_datetime(all_years, errors='coerce')
    min_year = all_years.dt.year.min()
    max_year = all_years.dt.year.max()
    # slider 默认值设为全范围
    st_years_filter = st.slider(
        '选择报表时间范围：',
        min_value=int(min_year),
        max_value=int(max_year),
        value=(int(max_year)-3, int(max_year))  # 默认选中整个范围
    )
    st_na_invisible = st.checkbox('🙈隐藏空行', True)
    # 只显示col_maps.xlsx中的item列
    st_show_col_maps_only = st.checkbox('🙈隐藏没在col_maps中的列', True)

# 筛选并保存报表数据
for report_name, df in reports.items():
    # 将结果保存在变量reports_quarter，方便后续调用，后续不用的话可以把下面语句注释掉
    if report_name == PROFIT_BY_REPORT:
        reports_quarter[PROFIT_BY_QUARTER] = get_quarter_report(df, '报告期')
    if report_name == CASH_BY_REPORT:
        reports_quarter[CASH_BY_QUARTER] = get_quarter_report(df, '报告期')

    # 1. slider年份筛选
    start_year, end_year = st_years_filter
    # 2. 隐藏空值筛选
    df_filtered = df[df['报告期'].dt.year.between(start_year, end_year)]
    if st_na_invisible:
        df_filtered = df_filtered.dropna(how='all', axis=1)
    # 3. col_maps中item列筛选
    if st_show_col_maps_only:
        df_filtered = df_filtered[[col for col in col_maps_dict[report_name]['item'] if col in df_filtered.columns]]


    # 将结果保存在变量reports_filtered，方便后续调用，后续不用的话可以把下面语句注释掉
    reports_filtered[report_name] = df_filtered
    # 计算过滤后df单季度的净利润和现金流报告
    # 将结果保存在变量reports_quarter_filtered，方便后续调用，后续不用的话可以把下面语句注释掉
    if report_name == PROFIT_BY_REPORT:
        reports_quarter_filtered[PROFIT_BY_QUARTER] = get_quarter_report(df_filtered, '报告期')
        # 经过单季度get_quarter_report计算可能导致某些行变成na，对单季度数据再次进行dropna筛选
        if st_na_invisible:
            reports_quarter_filtered[PROFIT_BY_QUARTER] = reports_quarter_filtered[PROFIT_BY_QUARTER].dropna(how='all', axis=1)
    if report_name == CASH_BY_REPORT:
        reports_quarter_filtered[CASH_BY_QUARTER] = get_quarter_report(df_filtered, '报告期')
        if st_na_invisible:
            reports_quarter_filtered[CASH_BY_QUARTER] = reports_quarter_filtered[CASH_BY_QUARTER].dropna(how='all', axis=1)
        


df_profit = reports_quarter_filtered[PROFIT_BY_QUARTER]
df_profit['毛利润'] = df_profit.eval("`营业总收入` - `营业成本`")
df_profit['核心利润'] = df_profit.eval(
    "`营业总收入` - `营业税金及附加` - `销售费用` - "
    "`管理费用` - `研发费用` - `财务费用`")
# 找到“营业总收入”的位置
idx = df_profit.columns.get_loc('营业总收入')
df_profit.insert(idx + 1, '净利润', df_profit.pop('净利润'))
# 插入“毛利润”，位置在营业总收入后面
df_profit.insert(idx + 2, '毛利润', df_profit.pop('毛利润'))
# 再插入“核心利润”，放在毛利润后面
df_profit.insert(idx + 3, '核心利润', df_profit.pop('核心利润'))


df_plot = reports_quarter_filtered[PROFIT_BY_QUARTER].copy()
df_plot[QUARTER] = df_plot['报告期'].dt.quarter.map(lambda x: f'Q{x}')
df_plot[YEAR] = df_plot['报告期'].dt.year

# print(df_plot.select_dtypes(include=['float', 'int']).info())
# # 显示所有数字列
# for col in df_plot.select_dtypes(include=['float', 'int']).columns: #['营业总收入','净利润']:
#     fig1, fig2 = plot_bar_quarter_group_px(df_plot, col)
#     st.plotly_chart(fig1, width='stretch')
#     st.plotly_chart(fig2, width='stretch')

# # 使用multiselect 过滤
selected = st.multiselect('选择要显示的列：', options=df_plot.select_dtypes(include=['float', 'int']).columns)
for col in selected: #['营业总收入','净利润']:
    fig1, fig2 = plot_bar_quarter_group_px(df_plot, col)
    st.plotly_chart(fig1, width='stretch', height=400)
    st.plotly_chart(fig2, width='stretch', height =400)

for report_name, df in reports_filtered.items():
    with st.expander(f'{report_name}'):
        df_filtered = df
        # 下面进行网页显示处理
        # 格式化'报告期'列显示格式
        df_filtered = df_filtered.map(value_to_str)
        # df转置并设置第一行报告期为列名
        df_filtered = df_filtered.T
        df_filtered.columns = df_filtered.iloc[0]
        df_filtered = df_filtered[1:]
        # 显示，空值替换为 '-'
        st.dataframe(df.map(value_to_str))

# for report_name, df in reports_quarter_filtered.items():
#     with st.expander(f'{report_name}'):
#         df_filtered = df
#         # 下面进行网页显示处理
#         # 格式化'报告期'列显示格式
#         df_filtered = df_filtered.map(value_to_str)
#         # df转置并设置第一行报告期为列名
#         df_filtered = df_filtered.T
#         df_filtered.columns = df_filtered.iloc[0]
#         df_filtered = df_filtered[1:]
#         # 显示，空值替换为 '-'
#         st.dataframe(df_filtered)


