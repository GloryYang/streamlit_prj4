import streamlit as st
import akshare as ak
import pandas as pd
import numpy as np
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict
import time, os

# all st element varaible with return value defined with prefix st_ in this code

# data source used by akshare - 'shown on web': 'called by function'
DATA_SOURCE = {'ths': 'ths', 'east money': 'em'}

# add 'SH' or 'SZ' as code prefix for east money data source
def add_prefix_to_code(code: str) -> str:
    code = code.strip()
    if code.startswith('6'):
        code = 'SH' + code
    if code.startswith(('0', '3')):
        code = 'SZ' + code
    return code

@st.cache_data
def get_stock_list() -> pd.DataFrame:
    df=pd.read_csv(r'stock_list1.csv', header=0)
    return df

# 资产负债表 - 报告期
@st.cache_data(ttl=3600, show_spinner=False)
def get_balance_sheet_by_report(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_debt_ths(symbol=code, indicator="按报告期")
    elif source == 'em':
        return ak.stock_balance_sheet_by_report_em(symbol=add_prefix_to_code(code))
    else:
        return pd.DataFrame()
# 利润表 - 报告期和季度 
@st.cache_data(ttl=3600, show_spinner=False)
def get_profit_sheet_by_report(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_benefit_ths(symbol=code, indicator="按报告期")
    elif source == 'em':
        return ak.stock_profit_sheet_by_report_em(symbol=add_prefix_to_code(code))
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
# 现金流量表 - 报告期和季度 
@st.cache_data(ttl=3600, show_spinner=False)
def get_cash_sheet_by_report(code: str, source: str = 'ths') -> pd.DataFrame:
    if source == 'ths':
        return ak.stock_financial_cash_ths(symbol=code, indicator="按报告期")
    elif source == 'em':
        return ak.stock_cash_flow_sheet_by_report_em(symbol=add_prefix_to_code(code))
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
def get_all_reports_concurrently(code: str, source: str = 'ths', max_worker: int =5) -> Dict[str, pd.DataFrame]:
    # five reports as tasks
    tasks = [('balance_sheet_by_report', get_balance_sheet_by_report, (code, source)),
             ('profit_sheet_by_report', get_profit_sheet_by_report, (code, source)),
             ('profit_sheet_by_quarterly', get_profit_sheet_by_quarterly, (code, source)),
             ('cash_sheet_by_report',get_cash_sheet_by_report, (code, source)),
             ('cash_sheet_by_quarterly', get_cash_sheet_by_quarterly, (code, source))]
    
    results= {}
    futures_to_tasks = {}
    with ThreadPoolExecutor(max_workers=max_worker) as executor:
            for t in tasks:
                # futures_to_tasks = {executor.submit(t[1], *t[2]): t[0]}
                futures_to_tasks[executor.submit(t[1], *t[2])]= t[0]

    
    for future in as_completed(futures_to_tasks.keys()):
        results[futures_to_tasks[future]] = future.result()

    return results




st.set_page_config(page_title="📈Finicial Report", layout="wide")
st.title("📈Finiacal Reprot Analysis")

with st.sidebar:
    st_data_source = st.selectbox('select data source:', ['ths', 'east money'], 0)
    # st_sheet_type = st.selectbox('select sheet type')

# =========================== stock list filter ================================================
# get stock list df
df_stock_list = get_stock_list()
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
    
st.subheader(f'📊 {stock_name}({stock_code}) 财务报表分析') # get stock code by stock_selected_row


with st.spinner("⏳ 正在下载数据，请稍候..."):
    # stock_balance_sheet_by_report = get_balance_sheet_by_report(stock_code, DATA_SOURCE[st_data_source])
    reports = get_all_reports_concurrently(st_stock_code, st_data_source)
st.success("✅ 数据下载完成！")

for name, df in reports.items():
    with st.expander(f'{name}'):
        df = df.astype(str).T
        df.columns = df.iloc[0]
        df = df.iloc[2:]
        st.dataframe(df)
print({name: "xx" for name in df.columns})
