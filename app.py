import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# =========================================================
# 基本設定
# =========================================================

st.set_page_config(
    page_title="Stock Finder AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

div[data-testid="stMetric"] {
    background-color: rgba(120,120,120,0.08);
    border-radius: 14px;
    padding: 15px;
}

.stock-card {
    border: 1px solid rgba(120,120,120,0.25);
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# 対象銘柄
# 後で数百〜数千銘柄に拡張可能
# =========================================================

STOCKS = {
    "INPEX": "1605.T",
    "大和ハウス工業": "1925.T",
    "積水ハウス": "1928.T",
    "JT": "2914.T",
    "日本製鉄": "5401.T",
    "三菱UFJ": "8306.T",
    "三井住友FG": "8316.T",
    "みずほFG": "8411.T",
    "三菱商事": "8058.T",
    "三井物産": "8031.T",
    "伊藤忠商事": "8001.T",
    "住友商事": "8053.T",
    "丸紅": "8002.T",
    "NTT": "9432.T",
    "KDDI": "9433.T",
    "ソフトバンク": "9434.T",
    "武田薬品工業": "4502.T",
    "アステラス製薬": "4503.T",
    "ブリヂストン": "5108.T",
    "キヤノン": "7751.T",
    "ホンダ": "7267.T",
    "トヨタ自動車": "7203.T",
    "MS&AD": "8725.T",
    "東京海上HD": "8766.T",
    "オリックス": "8591.T",
}


# =========================================================
# 共通関数
# =========================================================

def safe_number(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except:
        return default


def normalize_percent(value):
    """
    0.04 → 4%
    4.0  → 4%
    の両方に対応
    """
    value = safe_number(value)

    if value is None:
        return None

    if abs(value) <= 1:
        return value * 100

    return value


@st.cache_data(ttl=1800, show_spinner=False)
def get_stock_data(name, ticker):
    stock = yf.Ticker(ticker)

    try:
        info = stock.info
    except:
        info = {}

    try:
        hist = stock.history(period="1mo")
    except:
        hist = pd.DataFrame()

    price = safe_number(
        info.get("currentPrice")
        or info.get("regularMarketPrice")
    )

    # 株価がinfoで取れなければ履歴から取得
    if price is None and not hist.empty:
        price = safe_number(hist["Close"].iloc[-1])

    dividend_yield = normalize_percent(
        info.get("dividendYield")
    )

    per = safe_number(
        info.get("trailingPE")
    )

    forward_per = safe_number(
        info.get("forwardPE")
    )

    pbr = safe_number(
        info.get("priceToBook")
    )

    roe = normalize_percent(
        info.get("returnOnEquity")
    )

    equity_ratio = normalize_percent(
        info.get("totalCashPerShare")
    )

    payout_ratio = normalize_percent(
        info.get("payoutRatio")
    )

    market_cap = safe_number(
        info.get("marketCap")
    )

    previous_close = safe_number(
        info.get("previousClose")
    )

    change = None

    if price is not None and previous_close:
        change = (
            (price - previous_close)
            / previous_close
            * 100
        )

    return {
        "銘柄": name,
        "Ticker": ticker,
        "コード": ticker.replace(".T", ""),
        "株価": price,
        "配当利回り": dividend_yield,
        "PER": per,
        "予想PER": forward_per,
        "PBR": pbr,
        "ROE": roe,
        "配当性向": payout_ratio,
        "時価総額": market_cap,
        "騰落率": change,
    }


def calculate_score(row, mode):

    score = 0
    reasons = []

    dividend = row.get("配当利回り")
    per = row.get("PER")
    pbr = row.get("PBR")
    roe = row.get("ROE")
    payout = row.get("配当性向")

    # ---------------------------------
    # 高配当
    # ---------------------------------

    if dividend is not None:

        if dividend >= 5:
            score += 30
            reasons.append("配当利回り5%以上")

        elif dividend >= 4:
            score += 25
            reasons.append("配当利回り4%以上")

        elif dividend >= 3.5:
            score += 20
            reasons.append("配当利回り3.5%以上")

        elif dividend >= 3:
            score += 12

    # ---------------------------------
    # PER
    # ---------------------------------

    if per is not None:

        if 0 < per <= 8:
            score += 20
            reasons.append("PERがかなり低い")

        elif per <= 12:
            score += 17
            reasons.append("PERが低め")

        elif per <= 15:
            score += 12

        elif per <= 20:
            score += 6

    # ---------------------------------
    # PBR
    # ---------------------------------

    if pbr is not None:

        if 0 < pbr < 0.8:
            score += 15
            reasons.append("PBR0.8倍未満")

        elif pbr < 1:
            score += 12
            reasons.append("PBR1倍未満")

        elif pbr <= 1.5:
            score += 7

    # ---------------------------------
    # ROE
    # ---------------------------------

    if roe is not None:

        if roe >= 15:
            score += 20
            reasons.append("ROE15%以上")

        elif roe >= 10:
            score += 15
            reasons.append("ROE10%以上")

        elif roe >= 8:
            score += 10

    # ---------------------------------
    # 配当性向
    # ---------------------------------

    if payout is not None:

        if 20 <= payout <= 50:
            score += 15
            reasons.append("配当性向が適正")

        elif 50 < payout <= 70:
            score += 8

        elif payout > 100:
            score -= 10
            reasons.append("配当性向100%超に注意")

    # ---------------------------------
    # モード補正
    # ---------------------------------

    if mode == "💰 高配当":

        if dividend and dividend >= 4:
            score += 10

    elif mode == "🏷️ 割安":

        if per and per <= 12:
            score += 7

        if pbr and pbr <= 1:
            score += 7

    elif mode == "⚖️ バランス":

        if roe and roe >= 10:
            score += 5

        if dividend and dividend >= 3:
            score += 5

    score = min(max(round(score), 0), 100)

    return score, reasons


# =========================================================
# サイドバー
# =========================================================

st.sidebar.title("📊 Stock Finder")

mode = st.sidebar.radio(
    "投資スタイル",
    [
        "💰 高配当",
        "🏷️ 割安",
        "⚖️ バランス",
    ],
)

st.sidebar.divider()

dividend_min = st.sidebar.slider(
    "最低配当利回り",
    0.0,
    8.0,
    3.0,
    0.1,
)

per_max = st.sidebar.slider(
    "PER上限",
    5,
    50,
    20,
)

pbr_max = st.sidebar.slider(
    "PBR上限",
    0.5,
    5.0,
    2.0,
    0.1,
)

min_score = st.sidebar.slider(
    "最低スコア",
    0,
    100,
    40,
)

st.sidebar.caption(
    "※ 投資判断を自動化するものではなく、"
    "銘柄比較・スクリーニング用です。"
)


# =========================================================
# メイン画面
# =========================================================

st.title("📈 Stock Finder AI")

st.caption(
    "日本株を配当・割安度・収益性などから分析する"
    "株式スクリーニングアプリ"
)

tab1, tab2, tab3 = st.tabs([
    "🏆 おすすめランキング",
    "🔎 個別銘柄分析",
    "⭐ お気に入り",
])


# =========================================================
# ランキング
# =========================================================

with tab1:

    st.subheader("🏆 おすすめ株ランキング")

    if st.button(
        "🚀 最新データで分析",
        type="primary",
        use_container_width=True,
    ):

        progress = st.progress(0)

        rows = []

        total = len(STOCKS)

        for i, (name, ticker) in enumerate(STOCKS.items()):

            try:

                row = get_stock_data(
                    name,
                    ticker,
                )

                score, reasons = calculate_score(
                    row,
                    mode,
                )

                row["スコア"] = score
                row["評価ポイント"] = " / ".join(reasons)

                rows.append(row)

            except Exception:
                pass

            progress.progress(
                (i + 1) / total
            )

        progress.empty()

        if not rows:

            st.error(
                "株価データを取得できませんでした。"
            )

        else:

            df = pd.DataFrame(rows)

            # 条件フィルタ
            filtered = df.copy()

            filtered = filtered[
                filtered["スコア"] >= min_score
            ]

            filtered = filtered[
                filtered["配当利回り"].fillna(0)
                >= dividend_min
            ]

            filtered = filtered[
                filtered["PER"].fillna(999)
                <= per_max
            ]

            filtered = filtered[
                filtered["PBR"].fillna(999)
                <= pbr_max
            ]

            filtered = filtered.sort_values(
                "スコア",
                ascending=False,
            )

            st.session_state["result_df"] = filtered


    if "result_df" in st.session_state:

        df = st.session_state["result_df"]

        if df.empty:

            st.warning(
                "条件に合う銘柄がありません。"
                "条件を少し緩めてみてください。"
            )

        else:

            # --------------------------------
            # TOP3
            # --------------------------------

            st.subheader("🥇 TOP PICKS")

            top = df.head(3)

            cols = st.columns(3)

            medals = [
                "🥇",
                "🥈",
                "🥉",
            ]

            for i, (_, row) in enumerate(top.iterrows()):

                with cols[i]:

                    st.markdown(
                        f"### {medals[i]} {row['銘柄']}"
                    )

                    st.metric(
                        "スコア",
                        f"{int(row['スコア'])} / 100",
                    )

                    if pd.notna(row["株価"]):

                        st.metric(
                            "株価",
                            f"¥{row['株価']:,.0f}",
                        )

                    if pd.notna(row["配当利回り"]):

                        st.metric(
                            "配当利回り",
                            f"{row['配当利回り']:.2f}%",
                        )

            st.divider()

            # --------------------------------
            # 一覧
            # --------------------------------

            display_columns = [
                "銘柄",
                "コード",
                "スコア",
                "株価",
                "配当利回り",
                "PER",
                "PBR",
                "ROE",
                "配当性向",
                "騰落率",
                "評価ポイント",
            ]

            display_df = df[
                display_columns
            ].copy()

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "株価": st.column_config.NumberColumn(
                        format="¥%.0f"
                    ),
                    "配当利回り": st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
                    "ROE": st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
                    "配当性向": st.column_config.NumberColumn(
                        format="%.1f%%"
                    ),
                    "騰落率": st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
                    "スコア": st.column_config.ProgressColumn(
                        min_value=0,
                        max_value=100,
                    ),
                }
            )


# =========================================================
# 個別銘柄分析
# =========================================================

with tab2:

    st.subheader("🔎 個別銘柄分析")

    stock_code = st.text_input(
        "証券コード",
        placeholder="例：8306",
    )

    if st.button(
        "この銘柄を分析",
        use_container_width=True,
    ):

        if stock_code:

            ticker = (
                stock_code.strip()
                + ".T"
            )

            try:

                stock = yf.Ticker(ticker)

                info = stock.info

                company_name = (
                    info.get("longName")
                    or info.get("shortName")
                    or stock_code
                )

                row = get_stock_data(
                    company_name,
                    ticker,
                )

                score, reasons = calculate_score(
                    row,
                    mode,
                )

                st.header(company_name)

                st.caption(
                    f"証券コード：{stock_code}"
                )

                c1, c2, c3, c4 = st.columns(4)

                with c1:

                    if row["株価"] is not None:

                        st.metric(
                            "株価",
                            f"¥{row['株価']:,.0f}",
                        )

                with c2:

                    if row["配当利回り"] is not None:

                        st.metric(
                            "配当利回り",
                            f"{row['配当利回り']:.2f}%",
                        )

                with c3:

                    st.metric(
                        "PER",
                        (
                            f"{row['PER']:.1f}倍"
                            if row["PER"]
                            else "-"
                        ),
                    )

                with c4:

                    st.metric(
                        "総合スコア",
                        f"{score}/100",
                    )

                st.subheader("📊 評価")

                st.progress(
                    score / 100
                )

                for reason in reasons:

                    st.write(
                        f"✅ {reason}"
                    )

                # --------------------------------
                # チャート
                # --------------------------------

                st.subheader("📈 株価チャート")

                period = st.selectbox(
                    "期間",
                    [
                        "1mo",
                        "3mo",
                        "6mo",
                        "1y",
                        "2y",
                        "5y",
                    ],
                    index=3,
                )

                hist = stock.history(
                    period=period
                )

                if not hist.empty:

                    st.line_chart(
                        hist["Close"]
                    )

                # --------------------------------
                # 詳細
                # --------------------------------

                st.subheader("企業指標")

                metrics = pd.DataFrame({
                    "指標": [
                        "PER",
                        "予想PER",
                        "PBR",
                        "ROE",
                        "配当利回り",
                        "配当性向",
                    ],
                    "値": [
                        row["PER"],
                        row["予想PER"],
                        row["PBR"],
                        row["ROE"],
                        row["配当利回り"],
                        row["配当性向"],
                    ],
                })

                st.dataframe(
                    metrics,
                    hide_index=True,
                    use_container_width=True,
                )

                # --------------------------------
                # お気に入り
                # --------------------------------

                if "favorites" not in st.session_state:
                    st.session_state["favorites"] = {}

                if st.button(
                    "⭐ お気に入りに追加"
                ):

                    st.session_state[
                        "favorites"
                    ][stock_code] = company_name

                    st.success(
                        "お気に入りに追加しました"
                    )

            except Exception as e:

                st.error(
                    "銘柄データを取得できませんでした。"
                )


# =========================================================
# お気に入り
# =========================================================

with tab3:

    st.subheader("⭐ お気に入り")

    if "favorites" not in st.session_state:
        st.session_state["favorites"] = {}

    if not st.session_state["favorites"]:

        st.info(
            "お気に入り銘柄はまだありません。"
        )

    else:

        for code, name in (
            st.session_state["favorites"].items()
        ):

            st.write(
                f"⭐ {name}（{code}）"
            )


# =========================================================
# フッター
# =========================================================

st.divider()

st.caption(
    f"最終画面更新："
    f"{datetime.now().strftime('%Y/%m/%d %H:%M')}"
)

st.caption(
    "株価・財務データには取得遅延・欠損が発生する場合があります。"
)
