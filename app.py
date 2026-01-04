
import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed
import time, os, re

from common import *



@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_list() -> pd.DataFrame:
    df=pd.read_csv(r'stock_list1.csv', header=0)
    return df
@st.cache_data(ttl=3600, show_spinner=False)
# col_maps_dict {report_name: df in sheet_name['ths', 'em', 'sina', 'item', 'item_group']}
def get_col_maps_dict() -> dict[str, pd.DataFrame]:
    sheet_map = {PROFIT_BY_REPORT: 'profit',
                 BALANCE_BY_REPORT: 'balance',
                 CASH_BY_REPORT: 'cash',
                 PROFIT_BY_QUARTER: 'profit',
                 CASH_BY_QUARTER: 'cash',
                 PROFIT_PCT_BY_REPORT: 'profit',
                 PROFIT_PCT_BY_QUARTER: 'profit'
                 }
    # sheets_df is a dict. {sheet_name: df in each sheet}
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
@st.cache_data(ttl=3600, show_spinner=False)
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

# 计算报表新列，生成单季度和同比报表, reports使用的是全局变量
@st.cache_data(ttl=3600, show_spinner=False)
def reports_cal(reports_raw: dict, col_maps_dict: dict):
    reports = reports_raw #{k: v.copy() for k, v in reports_raw.items()}
    # 先格式化来自(ths, em, sina)的三张原始财务报表，统一格式，方便后续进行操作
    for report_name in [BALANCE_BY_REPORT, PROFIT_BY_REPORT, CASH_BY_REPORT]:
        df = reports[report_name]
        reports[report_name] = format_report(df, df_col_maps=col_maps_dict[report_name], source=DATA_SOURCE[st_data_source])

    ### ==================  计算新的数据列 计算自定义报表df ==================================
    ### 需要的表在这里先都计算好，后面再统一进行筛选
    ### 利润表 先计算自定义新列。然后计算 利润表-单季度df，利润表-报告期同比df， 利润表-单季度同比df'，自定义新列会被新的df继承
    df = reports[PROFIT_BY_REPORT]
    # 银行和保险行业的报表项目与传统项目不一样，先判断是否存在列名，再进行计算
    if '营业总收入' in df.columns:
        df['*营业总收入'] = df['营业总收入']
    # 2018年以前 研发费用属于管理费用，没有研发费用这一列，数据都是np.nan，需要用0来填充，否则计算出来的也是np.nan
    if '研发费用' in df.columns:
        df['研发费用'] = df['研发费用'].fillna(0)
    ### 利润表-报告期 中增加新的列
    if {'营业总收入','营业成本'}.issubset(df.columns):
        df['*毛利润'] = df.eval("`营业总收入` - `营业成本`")
    if {'营业总收入', '营业税金及附加', '营业成本', '销售费用', '管理费用', '研发费用', '财务费用'}.issubset(df.columns):
        df['*核心利润'] = df.eval("`营业总收入` - `营业税金及附加` - `营业成本` - `销售费用` - `管理费用` - `研发费用` - `财务费用`")
    # 2018年以前 研发费用属于管理费用，没有研发费用这一列
    elif {'营业总收入', '营业税金及附加', '营业成本', '销售费用', '管理费用', '财务费用'}.issubset(df.columns):
        df['*核心利润'] = df.eval("`营业总收入` - `营业税金及附加` - `营业成本` - `销售费用` - `管理费用` -  - `财务费用`")
    if '净利润' in df.columns:
        df['*净利润'] = df['净利润']
    if '归母净利润' in df.columns:
        df['*归母净利润'] = df['归母净利润']
    if '扣非净利润' in df.columns:
        df['*扣非净利润'] = df['扣非净利润']
    # 需判断计算得到的key_cols是否在df中存在，然后把key_cols放到前面
    key_cols = [col for col in ['*营业总收入', '*毛利润', '*核心利润', '*净利润', '*归母净利润', '*扣非净利润'] if col in df.columns]
    for idx, col in enumerate(key_cols):
        # 第一列为报告期，关键指标依次插入到报告期后面
        idx += 1
        df.insert(idx, col, df.pop(col))
    ### 计算 [利润表-单季度]df
    reports[PROFIT_BY_QUARTER] = get_quarter_report(df, REPORT_DATE)
    ### 计算 [利润表-报告期同比]df 和 [利润表-单季度同比]df，添加报告期列，保存到reports[PROFIT_PCT_BY_REPORT]和reports[PROFIT_PCT_BY_QUARTER]
    reports[PROFIT_PCT_BY_REPORT] = reports[PROFIT_BY_REPORT].select_dtypes(include=(float, int)).apply(safe_yoy)
    reports[PROFIT_PCT_BY_REPORT] = pd.concat([df[REPORT_DATE], reports[PROFIT_PCT_BY_REPORT] ], axis=1)
    reports[PROFIT_PCT_BY_QUARTER] = reports[PROFIT_BY_QUARTER].select_dtypes(include=(float, int)).apply(safe_yoy)
    reports[PROFIT_PCT_BY_QUARTER] = pd.concat([df[REPORT_DATE], reports[PROFIT_PCT_BY_QUARTER] ], axis=1)
    ### 计算 [利润表-报告期 和 利润表-单季度 的各种利润率和费用率]。这些指标不可进行同比计算，需要放到同比计算之后
    for report_name in [PROFIT_BY_REPORT, PROFIT_BY_QUARTER]:
        df = reports[report_name]
        if {'*毛利润', '营业总收入'}.issubset(df.columns):
            df['毛利润率[%]'] = df.eval('`*毛利润`/ `营业总收入` * 100')
        if {'*核心利润', '营业总收入'}.issubset(df.columns):
            df['核心利润率[%]'] = df.eval('`*核心利润`/ `营业总收入` * 100')
        if {'*净利润', '营业总收入'}.issubset(df.columns):
            df['净利润[%]'] = df.eval('`*净利润`/ `营业总收入` * 100') 
        if {'销售费用', '营业总收入'}.issubset(df.columns):
            df['销售费用率[%]'] = df.eval('`销售费用`/ `营业总收入` * 100')
        if {'管理费用', '营业总收入'}.issubset(df.columns):
            df['管理费用率[%]'] = df.eval('`管理费用`/ `营业总收入` * 100') 
        if {'研发费用', '营业总收入'}.issubset(df.columns):
            df['研发费用率[%]'] = df.eval('`研发费用`/ `营业总收入` * 100') 
        if {'财务费用', '营业总收入'}.issubset(df.columns):
            df['财务费用率[%]'] = df.eval('`财务费用`/ `营业总收入` * 100')
        if {'营业总收入', '销售费用', '管理费用', '研发费用', '财务费用'}.issubset(df.columns):
            df['四费费率[%]'] = df.eval("(`销售费用` + `管理费用` + `研发费用` + `财务费用`)/`营业总收入`*100")
        elif {'营业总收入', '销售费用', '管理费用', '财务费用'}.issubset(df.columns):
            df['三费费率[%]'] = df.eval("(`销售费用` + `管理费用` + `财务费用`)/`营业总收入`*100")

    ### 计算 [现金流-单季度]
    df= reports[CASH_BY_REPORT]
    reports[CASH_BY_QUARTER] = get_quarter_report(df, REPORT_DATE)

    ### 计算 [综合分析] 报表。先从各原始报表中取需要的数据列，再merg和sort
    profit_cols = [REPORT_DATE, '*营业总收入', '*毛利润', '*核心利润', '*净利润']
    balance_cols = [REPORT_DATE, '资产总计', '负债合计', '归属于母公司股东权益总计', '股东权益合计', 
                    '应收票据及应收账款', '应收款项融资', '存货', '固定资产合计', '商誉',
                    '应付票据及应付账款', '预收款项', '合同负债', '短期借款','长期借款', '应付债券']
    cash_cols = [REPORT_DATE, '期末现金及现金等价物余额', '销售商品、提供劳务收到的现金', '经营活动产生的现金流量净额',
                 '投资活动产生的现金流量净额', '筹资活动产生的现金流量净额']
    df1 = reports[PROFIT_BY_REPORT][[col for col in profit_cols if col in reports[PROFIT_BY_REPORT].columns]]
    df2 = reports[BALANCE_BY_REPORT][[col for col in balance_cols if col in reports[BALANCE_BY_REPORT].columns]]
    df3 = reports[CASH_BY_REPORT][[col for col in cash_cols if col in reports[CASH_BY_REPORT].columns]]
    reports[CROSS_REPORT] = pd.merge(left=df1, right=df2, how='outer', on=REPORT_DATE)
    df = reports[CROSS_REPORT]
    df = pd.merge(left=df, right=df3, how='outer', on=REPORT_DATE)
    df = df.sort_values(by=REPORT_DATE, axis=0, ascending=False).reset_index(drop=True)
    # 应收应付账款比[%]
    if {'应收票据及应收账款', '应收款项融资', '应付票据及应付账款'}.issubset(df.columns):
        df['应收应付账款比[%]'] = df.eval("(`应收票据及应收账款` + `应收款项融资` - `应付票据及应付账款`)/(`应收票据及应收账款` + `应收款项融资`) *100")
    elif {'应收票据及应收账款', '应付票据及应付账款'}.issubset(df.columns):
        df['应收应付账款比[%]'] = df.eval("(`应收票据及应收账款`  - `应付票据及应付账款`)/`应收票据及应收账款` *100")
    # 有息负债
    df['有息负债'] = 0
    for item in [col for col in ['短期借款','长期借款', '应付债券'] if col in df.columns]:
        df[item] = df[item].fillna(0)  # 避免na计算后产生na
        if item in df.columns:
            df['有息负债'] = df['有息负债'] + df[item]
    # 有息负债率[%]
    if {'有息负债', '期末现金及现金等价物余额'}.issubset(df.columns):
        df['有息负债率[%]'] = df['有息负债']/df['期末现金及现金等价物余额'] * 100
    # 应收总额营收比
    if {'*营业总收入', '应收票据及应收账款', '应收款项融资'}.issubset(df.columns):
        df['应收总额营收比[%]'] = (df['应收票据及应收账款'] + df['应收款项融资']) / df['*营业总收入'] * 100
    elif {'*营业总收入', '应收票据及应收账款'}.issubset(df.columns):
        df['应收总额营收比[%]'] = (df['应收票据及应收账款']) / df['*营业总收入'] * 100
    # 资产负债率[%]
    if {'负债合计', '资产总计'}.issubset(df.columns):
        df['资产负债率[%]'] = df['负债合计']/df['资产总计'] * 100
    # 固定资产总资产比[%]
    if {'固定资产合计', '资产总计'}.issubset(df.columns):
        df['固定资产总资产比[%]'] = df['固定资产合计']/df['资产总计'] * 100
    # 自定义列排序
    cal_cols = [col for col in ['应收应付账款比[%]', '有息负债', '有息负债率[%]', '应收总额营收比[%]', 
                '资产负债率[%]', '固定资产总资产比[%]'] if col in df.columns]
    for idx, col in enumerate(cal_cols):
        # 第一列为报告期，关键指标依次插入到报告期后面
        idx += 1
        df.insert(idx, col, df.pop(col))
    reports[CROSS_REPORT] = df  # merge函数产生新的dataframe，需要把df再赋值回去
    # st.write( reports[CROSS_REPORT])
    # st.stop()
    return reports


##########################################################################################
###############################  main start here #########################################
##########################################################################################
st.set_page_config(page_title="📈Financial Report", layout="wide")
st.title("📈Financial Reprot Analysis")

with st.sidebar:
    st_data_source = st.selectbox('select data source:', ['ths', 'east money', 'sina'], 0)
    # st_slide_years = st.slider()
    # st_sheet_type = st.selectbox('select sheet type')

# =========================== stock list filter ================================================
# get stock list df and df_col_maps
with st.spinner('⏳ 正在加载表格...'):
    df_stock_list = get_stock_list()
    col_maps_dict = get_col_maps_dict()
    df_stock_list['code'] = df_stock_list["code"].astype(str).str.zfill(6)

st_stock_code = st.text_input("ℹ️Please input stock code, name or initial (eg: 600519 or 贵州茅台 or gzmt):")

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
    df_stock_list_filterd.index += 1  # index for web-user should start from 1

    # show df_stock_list_filterd if not empty else show "no stock found"
    if not df_stock_list_filterd.empty:
        st.success(f"✅  {len(df_stock_list_filterd)} stock codes found as bellow:")
        st_stock_selected = st.dataframe(df_stock_list_filterd, width="stretch", 
                     height=(len(df_stock_list_filterd)+1)*35 if len(df_stock_list_filterd)<5 else 5*35,
                     selection_mode=['single-row'], on_select='rerun') 
        
        # df_stock_list_filterd只有一行时，不需要手动选择行，直接返回stock_selected_row=0，
        if len(df_stock_list_filterd) == 1:
            stock_selected_row = 0
        
        if len(st_stock_selected["selection"]["rows"])>0:
            # stock_selected format - {"selection":{"rows":[], "columns":[], "cells":[]}}
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


### ================= 下载三张原始报表，然后格式化报表，生成单季度和同比报表=================================
with st.spinner("⏳ 正在下载数据，请稍候..."):
    # stock_balance_sheet_by_report = get_balance_sheet_by_report(stock_code, DATA_SOURCE[st_data_source])
    reports_raw = {k: v for k, v in get_all_reports_concurrently(stock_code, DATA_SOURCE[st_data_source]).items()}
    # 计算报表新列，生成单季度和同比报表，使用cache_data修饰提升运行性能
    reports = reports_cal(reports_raw, col_maps_dict)
st.success("✅ 数据下载完成！")


### ==================================== sidebar筛选选项 =========================================
# 初始化st_quaters_filter，定义on_change函数防止季度选择为空，代码放到st.stop后面避免第一次没渲染按钮不高亮
QUARTERS_OPTION = ['Q1', 'Q2', 'Q3', 'Q4']
if 'st_quaters_filter' not in st.session_state:
    st.session_state.st_quaters_filter = QUARTERS_OPTION
    st.session_state.st_quaters_filter_pre = st.session_state.st_quaters_filter
def st_quaters_filter_change():
    # st_quaters_filter返回值是list
    if len(st.session_state.st_quaters_filter) == 0:
        st.session_state.st_quaters_filter = st.session_state.st_quaters_filter_pre
    st.session_state.st_quaters_filter_pre = st.session_state.st_quaters_filter

# 设置年份过滤
with st.sidebar:
    st.markdown('---')
    # 拼接三张原始报表的报告期列，获得最大年份和最小年份
    all_years = pd.concat([reports[report_name][REPORT_DATE] for report_name in [PROFIT_BY_REPORT, CASH_BY_REPORT, BALANCE_BY_REPORT]])
    # all_years = pd.to_datetime(all_years, errors='coerce')
    min_year = all_years.dt.year.min()
    max_year = all_years.dt.year.max()
    # slider 默认值设为全范围
    st_years_filter = st.slider(
        '选择报表时间范围：',
        min_value=int(min_year),
        max_value=int(max_year),
        value=(int(max_year)-5, int(max_year))  # 默认选中整个范围
    )
    # 季度筛选
    st_quarters_filter = st.segmented_control('选择显示的季度数据：', options=QUARTERS_OPTION, key='st_quaters_filter', on_change=st_quaters_filter_change, selection_mode='multi')
    st_quarters_filter = [int(q[1]) for q in st_quarters_filter]  # 从Q1中提取季度数字
    st_Q_latest = st.checkbox('最新季度', value=True)
    st.markdown('---')

    st_na_invisible = st.checkbox('🙈隐藏空行', True)
    # 只显示col_maps.xlsx中的item列
    st_show_col_maps_only = st.checkbox('🙈隐藏没在col_maps中的列', True)
    # 设置图标的高度
    st_chart_height = st.slider('图表高度：', min_value=200, max_value=600, value=300, step=1)

### ===================================  对报表进行筛选 ==========================================
### 对各报表进行筛选 1. slider年份筛选   2. 隐藏空值筛选   3. col_maps中item列筛选
start_year, end_year = st_years_filter
for report_name, df in reports.items():
    # 年份筛选
    df = df[df[REPORT_DATE].dt.year.between(start_year, end_year)]
    # 季度筛选
    df = df[df[REPORT_DATE].dt.quarter.isin(st_quarters_filter)]
    if st_Q_latest and df.iloc[0][REPORT_DATE]!=reports[report_name].iloc[0][REPORT_DATE]:
        new_row = reports[report_name].iloc[[0]]
        df = pd.concat([new_row, df], axis=0)
    reports_filtered[report_name] = df  
    if st_na_invisible:
        reports_filtered[report_name] = reports_filtered[report_name].dropna(how='all', axis=1)
    # 只有下面7张表需要进行col_maps筛选和排序，综合分析等列都是自定义的，不需要筛选
    if st_show_col_maps_only and report_name in [PROFIT_BY_REPORT, CASH_BY_REPORT, BALANCE_BY_REPORT, 
                                PROFIT_BY_QUARTER, CASH_BY_QUARTER, PROFIT_PCT_BY_REPORT, PROFIT_PCT_BY_QUARTER]:
        reports_filtered[report_name] = reports_filtered[report_name][[col for col in col_maps_dict[report_name]['item'] if col in reports_filtered[report_name].columns]]


### ======================================= 数据可视化  ==========================================
# 报表可视化category的segmented_control，使用on_change函数监测控件值，为空的话重置为前一个值
### 避坑：st_category默认按钮在第一次运行不会高亮。如果把session_state初始化放在最前面，中间的st.stop会打断st_category控件初始化和渲染。
# session_state初始化需要放到这里可以解决被st.stop打断。
CATEGORY_OPTIONS=['📋综合分析', '📊图表', '📅表格']
if 'st_category' not in st.session_state:
    st.session_state.st_category = CATEGORY_OPTIONS[1]
    st.session_state.st_category_pre = st.session_state.st_category
def st_category_change():
    # st_category返回值是字符串
    if st.session_state.st_category == None:
        st.session_state.st_category = st.session_state.st_category_pre
    st.session_state.st_category_pre = st.session_state.st_category


# st.write(time.strftime('%H:%M:%S'))
@st.fragment
def show_report_category():
    # 使用st.tabs没有局部刷新功能，改变tabs下的任何控件都会执行所有tabs下的代码，切换tab不再执行任何代码，切换会快，但是改变控件会耗时。st.tabs和st.segmented_control各有利弊
    # 使用st.segmented_control 可以进行局部刷新，fragment下的控件更新只更新fragment下的代码，fragment支持子fragment，可以做到局部中的局部刷新
    # tab1_summary, tab2_charts, tab3_tables = st.tabs(['📋综合分析', '📊图表', '📅表格'], default= '📅表格')
    st_category = st.segmented_control('选择显示分类：: ', key='st_category', on_change=st_category_change, options=CATEGORY_OPTIONS)
    # with tab1_summary:
    if st_category == CATEGORY_OPTIONS[0]:
        pass

    ### tab2 图表可视化
    # with tab2_charts:
    if st_category == CATEGORY_OPTIONS[1]:
        # 使用 segmented_control 来选择报表
        st_report_choice = st.segmented_control('选择报表：', options=[PROFIT_BY_REPORT, PROFIT_BY_QUARTER, CASH_BY_REPORT, CASH_BY_QUARTER, BALANCE_BY_REPORT], default=PROFIT_BY_QUARTER)
        # 图表 利润表-报告期 和 利润表-单季度
        if st_report_choice==PROFIT_BY_REPORT or st_report_choice==PROFIT_BY_QUARTER:
            if st_report_choice==PROFIT_BY_REPORT:
                df_plot1 = reports_filtered[PROFIT_BY_REPORT].copy()
                df_plot2 = reports_filtered[PROFIT_PCT_BY_REPORT].copy()
            if st_report_choice==PROFIT_BY_QUARTER:
                df_plot1 = reports_filtered[PROFIT_BY_QUARTER].copy()
                df_plot2 = reports_filtered[PROFIT_PCT_BY_QUARTER].copy()
            ### 使用multiselect 过滤
            cols = df_plot1.select_dtypes(include=['float', 'int']).columns
            # default_cols需要检测要显示的列是否存在，有些数据缺失可能没有计算出这些列（如银行和保险行业）
            default_cols = [col for col in ['*营业总收入', '*毛利润', '*核心利润', '*净利润', '*归母净利润', '*扣非净利润'] if col in cols]
            ### 避坑：实现multiselect defualt option记忆功能。本控件在if条件下，if在true和false切换后，控件会重新创建，
            # 所以使用key参数的session_state没有记忆功能，重新创建会重新初始化。可以在此处创建一个命名与本控件无关的session变量来保存和调用记忆。
            st_selected_cols = st.multiselect('选择要显示的列：', options=cols, default=default_cols)
            title_suffix = st_report_choice[st_report_choice.index('-')+1::]
            for col in st_selected_cols:
                fig1 = plot_bar_quarter_go(df_plot1, col, title_suffix=title_suffix, height=st_chart_height)
                st.plotly_chart(fig1, width='stretch')
                # 有些col在主df里面有，同比计算后可能没有，需要进行判断再画
                if col in df_plot2.columns:
                    fig2 = plot_bar_quarter_go(df_plot2, col, title_suffix=title_suffix + '同比', height=st_chart_height)
                    st.plotly_chart(fig2, width='stretch')

        # 图表 现金流量表-报告期 和 现金流量表-单季度
        if st_report_choice==CASH_BY_REPORT or st_report_choice==CASH_BY_QUARTER:
            df_plot1 = reports_filtered[st_report_choice].copy()
            cols = df_plot1.select_dtypes(include=['float', 'int']).columns
            default_cols = [col for col in ['销售商品、提供劳务收到的现金', '购建固定资产、无形资产和其他长期资产支付的现金', '取得子公司及其他营业单位支付的现金净额', 
                        '经营活动产生的现金流量净额', '投资活动产生的现金流量净额','筹资活动产生的现金流量净额'] if col in cols]
            st_selected_cols = st.multiselect('请选择要显示的列：', options=cols, default=default_cols)
            for col in st_selected_cols:
                fig1 = plot_bar_quarter_go(df_plot1, col, title_suffix='', height=st_chart_height)
                st.plotly_chart(fig1, width='stretch')
        # 图表 资产负债表-报告期
        if st_report_choice==BALANCE_BY_REPORT:
            df_plot1 = reports_filtered[st_report_choice].copy()
            cols = df_plot1.select_dtypes(include=['float', 'int']).columns
            default_cols = [col for col in ['应收票据及应收账款', '应收款项融资', '存货', 
                        '固定资产合计', '在建工程合计','商誉', '合同负债', '预收款项'] if col in cols]
            st_selected_cols = st.multiselect('请选择要显示的列：', options=cols, default=default_cols)
            for col in st_selected_cols:
                fig1 = plot_bar_quarter_go(df_plot1, col, title_suffix='', height=st_chart_height)
                st.plotly_chart(fig1, width='stretch')  


    # with tab3_tables:
    if st_category == CATEGORY_OPTIONS[2]:
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
                st.dataframe(df_filtered.map(value_to_str),
                    column_config={
                    "_index": st.column_config.Column(
                    "报告期",  # 可以在这里设置索引列的新标题
                    width=120 if '现金流量表' in report_name else 100,  # 调整宽度，例如 "small", "medium", "large"
                    ),
                    # 也可以在这里配置其他数据列...
                    })

show_report_category()


