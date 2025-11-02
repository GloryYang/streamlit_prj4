# =====================================
# 🌈 Streamlit 多页交互示例仪表盘
# =====================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.linear_model import LinearRegression
from datetime import datetime
import io

# 页面配置
st.set_page_config(page_title="多页Streamlit仪表盘", layout="wide", page_icon="📘")

# -------------------------------------
# 模拟数据生成函数
# -------------------------------------
@st.cache_data
def generate_data(n=36):
    np.random.seed(42)
    months = pd.date_range("2022-01-01", periods=n, freq="M")
    sales = np.random.randint(80, 200, n)
    profit = np.random.randint(10, 60, n)
    df = pd.DataFrame({"日期": months, "销售额": sales, "利润": profit})
    return df

df = generate_data()

# -------------------------------------
# 侧边栏导航
# -------------------------------------
st.sidebar.title("📂 导航菜单")
page = st.sidebar.selectbox(
    "选择页面：",
    ["📊 仪表盘", "🤖 AI预测", "📂 文件中心", "⚙️ 设置中心"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Streamlit 多页示例 | by GPT-5")

# -------------------------------------
# 页面一：仪表盘
# -------------------------------------
if page == "📊 仪表盘":
    st.title("📊 数据仪表盘")
    st.markdown("> 展示核心数据与趋势")

    # 布局
    col1, col2 = st.columns([3, 1])

    with col1:
        chart_type = st.selectbox("选择图表类型：", ["折线图", "柱状图", "散点图"])
        if chart_type == "折线图":
            fig = px.line(df, x="日期", y=["销售额", "利润"], markers=True)
        elif chart_type == "柱状图":
            fig = px.bar(df, x="日期", y=["销售额", "利润"], barmode="group")
        else:
            fig = px.scatter(df, x="销售额", y="利润", size="利润", color="日期")

        st.plotly_chart(fig, width="stretch")

    with col2:
        st.metric("📈 平均销售额", f"{df['销售额'].mean():.1f} 万元")
        st.metric("💰 平均利润", f"{df['利润'].mean():.1f} 万元")
        st.metric("🕒 数据点数", len(df))

    with st.expander("📋 查看原始数据"):
        st.dataframe(df, width="stretch")

# -------------------------------------
# 页面二：AI预测
# -------------------------------------
elif page == "🤖 AI预测":
    st.title("🤖 AI 销售趋势预测")
    st.markdown("> 使用线性回归模型预测未来销售额")

    months_ahead = st.slider("预测未来月数", 1, 12, 6)

    X = np.arange(len(df)).reshape(-1, 1)
    y = df["销售额"]
    model = LinearRegression().fit(X, y)

    future_idx = np.arange(len(df), len(df) + months_ahead).reshape(-1, 1)
    y_pred = model.predict(future_idx)

    df_pred = pd.DataFrame({
        "日期": pd.date_range(df["日期"].iloc[-1] + pd.offsets.MonthEnd(1), periods=months_ahead, freq="M"),
        "销售额": y_pred
    })

    df_all = pd.concat([df[["日期", "销售额"]], df_pred])
    df_all["类型"] = ["历史"] * len(df) + ["预测"] * len(df_pred)

    fig2 = px.line(df_all, x="日期", y="销售额", color="类型", markers=True,
                   title="销售额历史与预测")
    st.plotly_chart(fig2, width="stretch")

    st.success(f"✅ 已预测未来 {months_ahead} 个月销售额")

    st.dataframe(df_pred, width="stretch")

# -------------------------------------
# 页面三：文件中心
# -------------------------------------
elif page == "📂 文件中心":
    st.title("📂 文件上传与下载")
    st.markdown("> 支持上传 Excel / CSV 文件预览和导出")

    uploaded = st.file_uploader("上传文件", type=["csv", "xlsx"])
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df_file = pd.read_csv(uploaded)
            else:
                df_file = pd.read_excel(uploaded)
            st.dataframe(df_file.head(), width="stretch")
            st.success(f"文件加载成功：{uploaded.name}")
        except Exception as e:
            st.error(f"加载失败：{e}")

    # 导出Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="历史数据")
        writer.close()

    st.download_button(
        label="📥 下载历史数据 Excel",
        data=buffer.getvalue(),
        file_name="销售数据报告.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -------------------------------------
# 页面四：设置中心
# -------------------------------------
elif page == "⚙️ 设置中心":
    st.title("⚙️ 设置与个性化")
    st.markdown("> 尝试不同控件感受交互效果")

    theme = st.color_picker("🎨 主题颜色", "#4CAF50")
    username = st.text_input("🧑‍💻 用户名", "Yang")
    birthday = st.date_input("🎂 出生日期", datetime(1990, 1, 1))
    agree = st.checkbox("✅ 我已阅读并同意使用条款")

    if st.button("保存设置"):
        if agree:
            st.success(f"设置已保存，欢迎你 {username}！")
        else:
            st.warning("请勾选同意条款后再保存。")

    st.markdown("---")
    st.write("🎯 当前配置：")
    st.json({
        "用户名": username,
        "主题色": theme,
        "生日": str(birthday),
        "已同意条款": agree
    })

# -------------------------------------
# 页脚
# -------------------------------------
st.markdown("---")
st.caption("💡 Streamlit 多页应用示例 | 全面演示布局、控件与AI功能")
