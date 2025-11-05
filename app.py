import plotly.express as px
import streamlit as st
import os
import pandas as pd


@st.cache_data
def get_df():
    df=pd.read_csv('stock_list1.csv', header=0)
    return df

st.set_page_config(page_title="📈Finicial Report", layout="wide")
st.title("📈Finiacal Reprot Analysis")

# =========================== stock list filter ================================================
# get stock list df
df_stock_list = get_df()
df_stock_list['code'] = df_stock_list["code"].astype(str).str.zfill(6)

input_stock_code = st.text_input("ℹ️Please input stock code, name or initial (eg: 300416 or 汤臣倍健 or tcbj):")

df_stock_list_filterd = pd.DataFrame()
# filter df_stock_list with input as filter condition
input_stock_code = input_stock_code.strip()
if input_stock_code:
    # filter df with input
    df_stock_list_filterd = df_stock_list[(df_stock_list['code'].str.contains(input_stock_code, regex=False)) | 
                    df_stock_list['name'].str.contains(input_stock_code, regex=False) | df_stock_list['initial'].str.contains(input_stock_code.upper(), regex=False)]
    df_stock_list_filterd.reset_index(drop=True, inplace=True)
    df_stock_list_filterd.index += 1
    # show df_stock_list_filterd if not empty else show "no stock found"
    if not df_stock_list_filterd.empty:
        st.dataframe(df_stock_list_filterd, width="content", 
                     height=(len(df_stock_list_filterd)+1)*35 if len(df_stock_list_filterd)<5 else 5*35) # row height is 35
    else:
        st.error('no stock found')
st.markdown("---")
# ========================================================================

st.title("my title")
st.header("my header")
st.subheader("my subheader")
st.write('fisrt line')

st.markdown("# mark1")
st.markdown("## mark2")
st.markdown("### mark3")
st.markdown("#### mark4")
st.markdown("##### mark5")
st.markdown("###### mark6")
st.markdown("_italic_")
st.markdown("**bold**")

st.text_input("text input", "xxxx")



