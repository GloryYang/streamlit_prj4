import plotly.express as px
import streamlit as st
import os
import pandas as pd


@st.cache_data
def get_df():
    df=pd.read_csv('stock_list1.csv', header=0)
    return df
st.set_page_config(page_title="page tile", layout="wide")


df = get_df()
df['code'] = df["code"].astype(str).str.zfill(6)
input = st.text_input('input text')
df_filterd = pd.DataFrame()
if input:
    df_filterd = df[(df['code'].str.contains(input)) | df['name'].str.contains(input) | df['initial'].str.contains(input.upper())]

if not df_filterd.empty:
    st.dataframe(df_filterd)


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



