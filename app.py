import streamlit as st

st.set_page_config(
    page_title="おすすめ株アプリ",
    page_icon="📈",
    layout="wide"
)

st.title("📈 おすすめ株アプリ")

st.write("条件に合う日本株を探すアプリです。")

st.subheader("検索条件")

dividend = st.slider(
    "最低配当利回り（%）",
    min_value=0.0,
    max_value=10.0,
    value=3.5,
    step=0.1
)

equity_ratio = st.slider(
    "最低自己資本比率（%）",
    min_value=0,
    max_value=100,
    value=40
)

per = st.slider(
    "PER上限",
    min_value=1,
    max_value=50,
    value=15
)

if st.button("おすすめ株を検索"):
    st.success("検索機能は次のステップで追加します！")

    st.write("現在の条件")
    st.write(f"配当利回り：{dividend}%以上")
    st.write(f"自己資本比率：{equity_ratio}%以上")
    st.write(f"PER：{per}倍以下")
