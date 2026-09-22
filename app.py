import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from io import BytesIO
from datetime import datetime


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Stock Lens Japan",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>

.block-container {
    padding-top: 1.3rem;
    padding-bottom: 3rem;
}

div[data-testid="stMetric"] {
    border: 1px solid rgba(120,120,120,.20);
    padding: 15px;
    border-radius: 14px;
}

.small-note {
    color: #888;
    font-size: 13px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION
# ============================================================

if "favorites" not in st.session_state:
    st.session_state["favorites"] = {}


# ============================================================
# HELPER
# ============================================================

def safe_float(value, default=None):
    try:
        if value is None:
            return default

        value = float(value)

        if np.isnan(value):
            return default

        return value

    except:
        return default


def pct(value):

    value = safe_float(value)

    if value is None:
        return None

    # Yahooが0.04を返す場合
    if abs(value) <= 1:
        return value * 100

    return value


def fmt(value, digits=2, suffix=""):

    if value is None or pd.isna(value):
        return "-"

    return f"{value:.{digits}f}{suffix}"


# ============================================================
# JPX UNIVERSE
# ============================================================

@st.cache_data(ttl=86400)
def load_jpx_universe():

    """
    JPXの東証銘柄一覧。

    JPXの配布URLは差し替わる可能性があるため、
    取得できない場合は fallback 銘柄リストを返す。
    """

    # fallback
    fallback = pd.DataFrame([
        ["1605", "INPEX", "プライム"],
        ["1928", "積水ハウス", "プライム"],
        ["2914", "JT", "プライム"],
        ["4502", "武田薬品工業", "プライム"],
        ["5401", "日本製鉄", "プライム"],
        ["7203", "トヨタ自動車", "プライム"],
        ["7267", "本田技研工業", "プライム"],
        ["7751", "キヤノン", "プライム"],
        ["8001", "伊藤忠商事", "プライム"],
        ["8002", "丸紅", "プライム"],
        ["8031", "三井物産", "プライム"],
        ["8053", "住友商事", "プライム"],
        ["8058", "三菱商事", "プライム"],
        ["8306", "三菱UFJFG", "プライム"],
        ["8316", "三井住友FG", "プライム"],
        ["8411", "みずほFG", "プライム"],
        ["8591", "オリックス", "プライム"],
        ["8725", "MS&AD", "プライム"],
        ["8766", "東京海上HD", "プライム"],
        ["9432", "NTT", "プライム"],
        ["9433", "KDDI", "プライム"],
        ["9434", "ソフトバンク", "プライム"],
    ],
    columns=["コード", "銘柄名", "市場"]
    )

    return fallback


# ============================================================
# PRICE / FUNDAMENTAL
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_basic_data(code):

    ticker = f"{code}.T"

    stock = yf.Ticker(ticker)

    try:
        info = stock.info
    except:
        info = {}

    try:
        hist = stock.history(
            period="1y",
            auto_adjust=False
        )
    except:
        hist = pd.DataFrame()

    price = safe_float(
        info.get("currentPrice")
        or info.get("regularMarketPrice")
    )

    if price is None and not hist.empty:
        price = safe_float(
            hist["Close"].dropna().iloc[-1]
        )

    previous_close = safe_float(
        info.get("previousClose")
    )

    dividend_yield = pct(
        info.get("dividendYield")
    )

    per = safe_float(
        info.get("trailingPE")
    )

    forward_per = safe_float(
        info.get("forwardPE")
    )

    pbr = safe_float(
        info.get("priceToBook")
    )

    roe = pct(
        info.get("returnOnEquity")
    )

    payout = pct(
        info.get("payoutRatio")
    )

    market_cap = safe_float(
        info.get("marketCap")
    )

    current_ratio = safe_float(
        info.get("currentRatio")
    )

    debt_to_equity = safe_float(
        info.get("debtToEquity")
    )

    change_1d = None

    if price and previous_close:
        change_1d = (
            price / previous_close - 1
        ) * 100


    # 52週
    high52 = None
    low52 = None
    year_return = None

    if not hist.empty:

        close = hist["Close"].dropna()

        if len(close):

            high52 = float(close.max())
            low52 = float(close.min())

            if len(close) > 1:
                year_return = (
                    close.iloc[-1]
                    / close.iloc[0]
                    - 1
                ) * 100


    high_gap = None

    if price and high52:
        high_gap = (
            price / high52 - 1
        ) * 100


    return {
        "コード": code,
        "株価": price,
        "配当利回り": dividend_yield,
        "PER": per,
        "予想PER": forward_per,
        "PBR": pbr,
        "ROE": roe,
        "配当性向": payout,
        "時価総額": market_cap,
        "流動比率": current_ratio,
        "D/E": debt_to_equity,
        "前日比": change_1d,
        "52週高値": high52,
        "52週安値": low52,
        "52週高値乖離": high_gap,
        "1年騰落率": year_return,
    }


# ============================================================
# DIVIDEND HISTORY
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_dividend_history(code):

    ticker = f"{code}.T"

    stock = yf.Ticker(ticker)

    try:
        price = stock.history(
            period="6y",
            auto_adjust=False
        )

        dividends = stock.dividends

    except:
        return None


    if price.empty or dividends.empty:
        return None


    price = price.copy()
    dividends = dividends.copy()


    # 年平均株価
    annual_price = (
        price["Close"]
        .dropna()
        .groupby(price.index.year)
        .mean()
    )


    # 年間配当
    annual_dividend = (
        dividends
        .groupby(dividends.index.year)
        .sum()
    )


    rows = []


    for year in sorted(
        set(annual_price.index)
        & set(annual_dividend.index)
    ):

        avg_price = safe_float(
            annual_price.loc[year]
        )

        dividend = safe_float(
            annual_dividend.loc[year]
        )

        if not avg_price or not dividend:
            continue

        yield_pct = (
            dividend / avg_price
        ) * 100

        rows.append({
            "年": int(year),
            "年間配当": dividend,
            "年平均株価": avg_price,
            "配当利回り": yield_pct,
        })


    if not rows:
        return None


    df = pd.DataFrame(rows)

    df = df.sort_values("年")


    # 直近5年
    df5 = df.tail(5).copy()


    avg_yield = safe_float(
        df5["配当利回り"].mean()
    )


    # 減配回数
    dividend_diff = (
        df5["年間配当"]
        .diff()
    )

    cut_count = int(
        (dividend_diff < 0).sum()
    )


    # 増配年数
    increase_count = int(
        (dividend_diff > 0).sum()
    )


    # 5年配当成長率
    dividend_growth = None

    if len(df5) >= 2:

        first = df5["年間配当"].iloc[0]
        last = df5["年間配当"].iloc[-1]

        years = (
            df5["年"].iloc[-1]
            - df5["年"].iloc[0]
        )

        if first > 0 and last > 0 and years > 0:

            dividend_growth = (
                (last / first)
                ** (1 / years)
                - 1
            ) * 100


    return {
        "table": df5,
        "平均利回り5年": avg_yield,
        "減配回数": cut_count,
        "増配回数": increase_count,
        "配当CAGR": dividend_growth,
    }


# ============================================================
# PRICE RISK
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_price_risk(code):

    ticker = f"{code}.T"

    try:

        hist = yf.download(
            ticker,
            period="5y",
            auto_adjust=True,
            progress=False,
        )

    except:

        return {}


    if hist.empty:
        return {}


    close = hist["Close"]

    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]


    close = close.dropna()


    if len(close) < 2:
        return {}


    rolling_max = close.cummax()

    drawdown = (
        close / rolling_max - 1
    )


    max_dd = (
        drawdown.min()
        * 100
    )


    volatility = (
        close.pct_change()
        .std()
        * np.sqrt(252)
        * 100
    )


    return {
        "最大DD": float(max_dd),
        "ボラティリティ": float(volatility),
    }


# ============================================================
# SCORE
# ============================================================

def calculate_score(data):

    score = 0

    breakdown = {
        "配当": 0,
        "割安": 0,
        "収益性": 0,
        "配当安定": 0,
        "株価水準": 0,
    }


    dy = data.get("配当利回り")
    avg = data.get("平均利回り5年")
    per = data.get("PER")
    pbr = data.get("PBR")
    roe = data.get("ROE")
    payout = data.get("配当性向")
    cuts = data.get("減配回数")
    growth = data.get("配当CAGR")
    high_gap = data.get("52週高値乖離")


    # 配当 25
    if dy:

        if dy >= 5:
            breakdown["配当"] = 25

        elif dy >= 4:
            breakdown["配当"] = 22

        elif dy >= 3.5:
            breakdown["配当"] = 18

        elif dy >= 3:
            breakdown["配当"] = 12


    # 割安 25
    value_score = 0

    if per:

        if 0 < per <= 10:
            value_score += 12

        elif per <= 15:
            value_score += 8

        elif per <= 20:
            value_score += 4


    if pbr:

        if 0 < pbr <= 0.8:
            value_score += 13

        elif pbr <= 1:
            value_score += 10

        elif pbr <= 1.5:
            value_score += 5


    breakdown["割安"] = min(
        value_score,
        25
    )


    # 収益性 20
    if roe:

        if roe >= 15:
            breakdown["収益性"] = 20

        elif roe >= 10:
            breakdown["収益性"] = 15

        elif roe >= 8:
            breakdown["収益性"] = 10


    # 配当安定性 20
    stable = 0

    if cuts is not None:

        if cuts == 0:
            stable += 10

        elif cuts == 1:
            stable += 5


    if growth is not None:

        if growth >= 8:
            stable += 10

        elif growth >= 3:
            stable += 7

        elif growth >= 0:
            stable += 4


    breakdown["配当安定"] = min(
        stable,
        20
    )


    # 株価水準 10
    if high_gap is not None:

        if high_gap <= -30:
            breakdown["株価水準"] = 10

        elif high_gap <= -20:
            breakdown["株価水準"] = 8

        elif high_gap <= -10:
            breakdown["株価水準"] = 5


    # 利回り平均との差補正
    if dy and avg:

        premium = dy - avg

        if premium >= 1:
            breakdown["株価水準"] += 5

        elif premium >= 0.5:
            breakdown["株価水準"] += 3


    breakdown["株価水準"] = min(
        breakdown["株価水準"],
        10
    )


    score = sum(
        breakdown.values()
    )


    return min(
        round(score),
        100
    ), breakdown


# ============================================================
# FULL ANALYSIS
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def analyze_stock(
    code,
    name=""
):

    basic = get_basic_data(code)

    dividend = get_dividend_history(code)

    risk = get_price_risk(code)


    data = {
        **basic,
        **risk,
    }


    data["銘柄名"] = name


    if dividend:

        data["平均利回り5年"] = dividend[
            "平均利回り5年"
        ]

        data["減配回数"] = dividend[
            "減配回数"
        ]

        data["増配回数"] = dividend[
            "増配回数"
        ]

        data["配当CAGR"] = dividend[
            "配当CAGR"
        ]

        data["配当履歴"] = dividend[
            "table"
        ]

    else:

        data["平均利回り5年"] = None
        data["減配回数"] = None
        data["増配回数"] = None
        data["配当CAGR"] = None
        data["配当履歴"] = None


    # 利回りプレミアム
    current = data.get(
        "配当利回り"
    )

    avg = data.get(
        "平均利回り5年"
    )


    if current and avg:

        data[
            "利回り平均との差"
        ] = current - avg

        data[
            "利回り倍率"
        ] = current / avg

    else:

        data[
            "利回り平均との差"
        ] = None

        data[
            "利回り倍率"
        ] = None


    score, breakdown = calculate_score(
        data
    )


    data["総合スコア"] = score
    data["スコア内訳"] = breakdown


    return data


# ============================================================
# HUMAN COMMENT
# ============================================================

def make_plain_comment(data):

    lines = []


    current = data.get(
        "配当利回り"
    )

    avg = data.get(
        "平均利回り5年"
    )

    premium = data.get(
        "利回り平均との差"
    )

    cuts = data.get(
        "減配回数"
    )

    growth = data.get(
        "配当CAGR"
    )

    high_gap = data.get(
        "52週高値乖離"
    )


    if current is not None:

        lines.append(
            f"現在の配当利回りは "
            f"{current:.2f}%です。"
        )


    if avg is not None and premium is not None:

        if premium > 0:

            lines.append(
                f"過去5年平均 "
                f"{avg:.2f}% "
                f"より {premium:.2f}pt 高い水準です。"
            )

        else:

            lines.append(
                f"過去5年平均 "
                f"{avg:.2f}% "
                f"より {abs(premium):.2f}pt 低い水準です。"
            )


    if cuts is not None:

        lines.append(
            f"直近5年間の減配は "
            f"{cuts}回です。"
        )


    if growth is not None:

        lines.append(
            f"年間配当の5年成長率は "
            f"{growth:.1f}%程度です。"
        )


    if high_gap is not None:

        lines.append(
            f"現在株価は52週高値から "
            f"{abs(high_gap):.1f}%下です。"
        )


    return " ".join(lines)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "Stock Lens"
)

mode = st.sidebar.radio(
    "表示モード",
    [
        "高配当",
        "割安",
        "安定配当",
        "逆張り",
    ]
)

st.sidebar.divider()

market_filter = st.sidebar.multiselect(
    "市場",
    [
        "プライム",
        "スタンダード",
        "グロース",
    ],
    default=[
        "プライム",
    ],
)

min_yield = st.sidebar.slider(
    "最低配当利回り",
    0.0,
    8.0,
    3.0,
    0.1,
)

max_per = st.sidebar.slider(
    "PER上限",
    5,
    60,
    25,
)

max_pbr = st.sidebar.slider(
    "PBR上限",
    0.5,
    10.0,
    3.0,
    0.1,
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "📊 Stock Lens Japan"
)

st.caption(
    "日本株を配当・割安度・収益性・過去水準から比較"
)


tabs = st.tabs([
    "🔎 銘柄検索",
    "🏆 ランキング",
    "⭐ お気に入り",
    "ℹ️ 指標説明",
])


# ============================================================
# SEARCH
# ============================================================

with tabs[0]:

    universe = load_jpx_universe()

    search = st.text_input(
        "銘柄名または証券コード",
        placeholder="例：8306 / 三菱UFJ",
    )


    candidates = universe.copy()


    if search:

        candidates = candidates[

            candidates["コード"]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False
            )

            |

            candidates["銘柄名"]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False
            )

        ]


    if not candidates.empty:

        option = st.selectbox(
            "銘柄",
            candidates.apply(
                lambda r:
                f"{r['コード']}  {r['銘柄名']}",
                axis=1
            )
        )


        code = option.split()[0]

        name = candidates[
            candidates["コード"]
            .astype(str)
            == code
        ]["銘柄名"].iloc[0]


        if st.button(
            "分析する",
            type="primary",
            use_container_width=True,
        ):

            with st.spinner(
                "株価・配当履歴を分析しています..."
            ):

                data = analyze_stock(
                    code,
                    name
                )


            st.header(
                f"{name}  {code}"
            )


            c1,c2,c3,c4 = st.columns(4)


            c1.metric(
                "株価",
                (
                    f"¥{data['株価']:,.0f}"
                    if data.get("株価")
                    else "-"
                )
            )


            c2.metric(
                "現在利回り",
                fmt(
                    data.get("配当利回り"),
                    2,
                    "%"
                )
            )


            c3.metric(
                "5年平均利回り",
                fmt(
                    data.get("平均利回り5年"),
                    2,
                    "%"
                )
            )


            premium = data.get(
                "利回り平均との差"
            )


            c4.metric(
                "平均との差",
                (
                    f"{premium:+.2f}pt"
                    if premium is not None
                    else "-"
                )
            )


            st.divider()


            c1,c2,c3,c4 = st.columns(4)


            c1.metric(
                "PER",
                fmt(
                    data.get("PER"),
                    1,
                    "倍"
                )
            )


            c2.metric(
                "PBR",
                fmt(
                    data.get("PBR"),
                    2,
                    "倍"
                )
            )


            c3.metric(
                "ROE",
                fmt(
                    data.get("ROE"),
                    1,
                    "%"
                )
            )


            c4.metric(
                "総合スコア",
                f"{data['総合スコア']}/100"
            )


            st.progress(
                data[
                    "総合スコア"
                ] / 100
            )


            st.subheader(
                "数字で見る現在の位置"
            )


            st.info(
                make_plain_comment(
                    data
                )
            )


            # 配当履歴
            hist = data.get(
                "配当履歴"
            )


            if hist is not None:

                st.subheader(
                    "配当利回り推移"
                )

                chart = (
                    hist
                    .set_index("年")[
                        "配当利回り"
                    ]
                )

                st.line_chart(
                    chart
                )


                st.dataframe(
                    hist,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "年間配当":
                        st.column_config.NumberColumn(
                            format="¥%.2f"
                        ),

                        "年平均株価":
                        st.column_config.NumberColumn(
                            format="¥%.0f"
                        ),

                        "配当利回り":
                        st.column_config.NumberColumn(
                            format="%.2f%%"
                        ),
                    }
                )


            st.subheader(
                "スコア内訳"
            )


            score_df = pd.DataFrame(
                list(
                    data[
                        "スコア内訳"
                    ].items()
                ),
                columns=[
                    "項目",
                    "点数"
                ]
            )


            st.dataframe(
                score_df,
                hide_index=True,
                use_container_width=True,
            )


            if st.button(
                "⭐ お気に入りに追加"
            ):

                st.session_state[
                    "favorites"
                ][code] = name

                st.success(
                    "追加しました"
                )


# ============================================================
# RANKING
# ============================================================

with tabs[1]:

    st.subheader(
        "ランキング"
    )

    universe = load_jpx_universe()


    universe = universe[
        universe[
            "市場"
        ].isin(
            market_filter
        )
    ]


    st.write(
        f"対象銘柄数：{len(universe):,}"
    )


    limit = st.selectbox(
        "一度に分析する銘柄数",
        [
            10,
            25,
            50,
            100,
        ],
        index=1,
    )


    st.caption(
        "全銘柄の詳細分析は時間がかかるため、"
        "候補を段階的に分析します。"
    )


    if st.button(
        "ランキングを作成",
        type="primary",
        use_container_width=True,
    ):

        rows = []


        progress = st.progress(0)


        sample = universe.head(
            limit
        )


        for i, row in enumerate(
            sample.itertuples()
        ):

            try:

                data = analyze_stock(
                    str(row.コード),
                    row.銘柄名
                )


                if (
                    data.get(
                        "配当利回り"
                    ) is not None

                    and data[
                        "配当利回り"
                    ] >= min_yield
                ):

                    if (
                        data.get("PER") is None
                        or data["PER"] <= max_per
                    ):

                        if (
                            data.get("PBR") is None
                            or data["PBR"] <= max_pbr
                        ):

                            rows.append(
                                data
                            )

            except:
                pass


            progress.progress(
                (i + 1)
                / len(sample)
            )


        progress.empty()


        if rows:

            df = pd.DataFrame(
                rows
            )


            df = df.sort_values(
                "総合スコア",
                ascending=False
            )


            columns = [
                "銘柄名",
                "コード",
                "総合スコア",
                "株価",
                "配当利回り",
                "平均利回り5年",
                "利回り平均との差",
                "利回り倍率",
                "PER",
                "PBR",
                "ROE",
                "配当CAGR",
                "減配回数",
                "52週高値乖離",
                "最大DD",
            ]


            display = df[
                columns
            ]


            st.dataframe(
                display,
                hide_index=True,
                use_container_width=True,
            )


            csv = (
                display
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8-sig"
                )
            )


            st.download_button(
                "CSVダウンロード",
                csv,
                "stock_ranking.csv",
                "text/csv",
            )


        else:

            st.warning(
                "条件に合う銘柄がありません。"
            )


# ============================================================
# FAVORITES
# ============================================================

with tabs[2]:

    st.subheader(
        "お気に入り"
    )


    if not st.session_state[
        "favorites"
    ]:

        st.info(
            "お気に入りはまだありません。"
        )


    else:

        for code,name in (
            st.session_state[
                "favorites"
            ].items()
        ):

            st.write(
                f"⭐ {code} {name}"
            )


# ============================================================
# HELP
# ============================================================

with tabs[3]:

    st.subheader(
        "指標の見方"
    )


    st.markdown("""
**現在利回り**  
現在の株価に対する年間配当の割合。

**5年平均利回り**  
過去5年間の各年の年間配当と平均株価から計算した平均値。

**平均との差**  
現在利回り − 5年平均利回り。

**利回り倍率**  
現在利回り ÷ 5年平均利回り。

**52週高値乖離**  
現在株価が直近52週の高値から何％離れているか。

**最大DD**  
過去5年間で最も大きかった株価下落率。

**配当CAGR**  
年間配当の年平均成長率。
""")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "本アプリは銘柄比較用です。"
    "表示データには遅延・欠損・取得元との差異が生じる場合があります。"
)

st.caption(
    datetime.now().strftime(
        "画面更新 %Y/%m/%d %H:%M"
    )
)
