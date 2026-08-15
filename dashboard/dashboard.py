# ============================================================
# ZERODHA AI FINANCIAL INTELLIGENCE - STREAMLIT DASHBOARD
# ============================================================
import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
# ============================================================
# AI - DIRECT IN-PROCESS INTEGRATION
# ============================================================
from AI.chat_chain import run_chat_chain
from AI.health_score import portfolio_health_score
from AI.risk_analysis import portfolio_risk_analysis
from AI.portfolio_summary import generate_portfolio_summary
from AI.improvement import portfolio_improvement_suggestions
# ============================================================
# SERVICES
# ============================================================
from services.portfolio import (
    read_portfolio,
    valid_coloumn,
    clean_data,
)
from services.market import (
    updated_current_price,
    get_stock_info,
    get_market_data,
)
from services.news import (
    get_stock_news,
)
# ============================================================
# ANALYTICS
# ============================================================

from Analytics.portfolio_analytics import (
    calculate_total_investment,
    calculate_current_value,
    calculate_profit_loss,
    calculate_profit_loss_percentage,
    calculate_portfolio_summary,
)
from Analytics.sector_analysis import (
    compute_sector_breakdown,
)
# ============================================================
# DATA CONVERSION HELPERS
# ============================================================
def prepare_portfolio_payload(portfolio_df):
    """Convert DataFrame into JSON-safe records for the AI chain."""

    if portfolio_df is None or portfolio_df.empty:
        return []
    safe_df = portfolio_df.copy()
    safe_df = safe_df.where(pd.notnull(safe_df), None)
    return safe_df.to_dict(orient="records")
def prepare_news_payload(news_data):
    """Normalize cached news so the hybrid AI chain can use it."""
    normalized = {}
    for stock, articles in (news_data or {}).items():
        normalized[stock] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            normalized[stock].append(
                {
                    "title": article.get(
                        "Title",
                        article.get("title", ""),
                    ),
                    "description": article.get(
                        "Description",
                        article.get("description", ""),
                    ),
                    "source": article.get("source", ""),
                    "published": article.get("published", ""),
                }
            )
    return normalized
# ============================================================
# NUMERIC / CHART HELPERS
# ============================================================
def to_numeric_series(series):
    """
    Convert portfolio values such as:
    ₹1,234.50, 1,234.50, '1234.50', None
    into numeric values safely.
    """
    cleaned = (
        series.astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip()
        .replace(
            {
                "": None,
                "None": None,
                "nan": None,
                "NaN": None,
            }
        )
    )
    return pd.to_numeric(
        cleaned,
        errors="coerce",
    )
def safe_plotly_chart(fig):
    """
    Render Plotly reliably across local and deployed Streamlit.
    """
    try:
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )
    except TypeError:
        # Newer Streamlit versions prefer width="stretch".
        st.plotly_chart(
            fig,
            width="stretch",
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )
# ============================================================
# HISTORICAL MARKET DATA
# ============================================================
def get_historical_data(
    symbols,
    period="1y",
):
    """
    Fetch historical closing prices.
    """
    historical_data = []
    for symbol in symbols:
        try:
            yahoo_symbol = (
                f"{symbol}.NS"
            )
            stock = yf.Ticker(
                yahoo_symbol
            )
            history = stock.history(
                period=period,
                auto_adjust=False,
            )
            if history.empty:
                continue
            history = (
                history.reset_index()
            )
            history["Stock Symbol"] = (
                symbol
            )
            history = history[
                [
                    "Date",
                    "Stock Symbol",
                    "Close",
                ]
            ]
            history = history.dropna(
                subset=["Close"]
            )
            historical_data.append(
                history
            )
        except Exception as error:
            print(
                "Historical data error "
                f"for {symbol}: {error}"
            )
    if not historical_data:
        return pd.DataFrame()
    return pd.concat(
        historical_data,
        ignore_index=True,
    )
# ============================================================
# MAIN APP
# ============================================================
def main():
    # ========================================================
    # PAGE CONFIG
    # ========================================================
    st.set_page_config(
        page_title=(
            "Zerodha AI Financial Intelligence"
        ),
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # ========================================================
    # SESSION STATE
    # ========================================================
    if "portfolio_data" not in st.session_state:
        st.session_state.portfolio_data = None
    if "news_data" not in st.session_state:
        st.session_state.news_data = {}
    if "file_name" not in st.session_state:
        st.session_state.file_name = None
    if "health_result" not in st.session_state:
        st.session_state.health_result = None
    if "risk_result" not in st.session_state:
        st.session_state.risk_result = None
    if "summary_result" not in st.session_state:
        st.session_state.summary_result = None
    if "improvement_result" not in st.session_state:
        st.session_state.improvement_result = None
    if "stock_ai_result" not in st.session_state:
        st.session_state.stock_ai_result = None
    if "rag_answer" not in st.session_state:
        st.session_state.rag_answer = None
    if "chat_answer" not in st.session_state:
        st.session_state.chat_answer = None
    # ========================================================
    # HEADER
    # ========================================================
    st.title(
        "📊 Zerodha AI Financial Intelligence"
    )
    st.caption(
        "Portfolio Analytics • Market Data • "
        "News • AI Insights"
    )
    # ========================================================
    # SIDEBAR
    # ========================================================
    with st.sidebar:
        st.header(
            "📁 Portfolio"
        )
        uploaded_file = st.file_uploader(
            "Upload Portfolio",
            type=["csv", "xlsx"],
        )
        st.divider()
        if (
            st.session_state
            .portfolio_data
            is not None
        ):
            st.success(
                "Portfolio loaded"
            )
            if st.session_state.file_name:
                st.caption(
                    "File: "
                    f"{st.session_state.file_name}"
                )
            if st.button(
                "🔄 Refresh Market Data",
                width="stretch",
            ):
                try:
                    with st.spinner(
                        "Updating market data..."
                    ):
                        df = (
                            st.session_state
                            .portfolio_data
                            .copy()
                        )
                        df = (
                            updated_current_price(
                                df
                            )
                        )
                        (
                            st.session_state
                            .portfolio_data
                        ) = df
                    st.success(
                        "Market data updated"
                    )
                except Exception as error:
                    st.error(
                        "Market data update "
                        f"failed: {error}"
                    )
    # ========================================================
    # LOAD PORTFOLIO
    # ========================================================
    if uploaded_file is not None:
        new_file = (
            st.session_state.file_name
            != uploaded_file.name
        )
        if new_file:
            try:
                with st.spinner(
                    "Reading portfolio..."
                ):
                    portfolio = (
                        read_portfolio(
                            uploaded_file
                        )
                    )
                missing_columns = (
                    valid_coloumn(
                        portfolio
                    )
                )
                if missing_columns:
                    st.error(
                        "Missing required columns: "
                        + ", ".join(
                            missing_columns
                        )
                    )
                    st.stop()
                portfolio = clean_data(
                    portfolio
                )
                with st.spinner(
                    "Fetching live market data..."
                ):

                    portfolio = (
                        updated_current_price(
                            portfolio
                        )
                    )
                (
                    st.session_state
                    .portfolio_data
                ) = portfolio
                st.session_state.file_name = (
                    uploaded_file.name
                )
                st.session_state.news_data = {}
                st.session_state.health_result = None
                st.session_state.risk_result = None
                st.session_state.summary_result = None
                st.session_state.improvement_result = None
                st.session_state.stock_ai_result = None
                st.session_state.rag_answer = None
                st.session_state.chat_answer = None
            except Exception as error:
                st.error(
                    "Unable to process portfolio: "
                    f"{error}"
                )
                st.stop()
    # ========================================================
    # NO PORTFOLIO
    # ========================================================
    if (
        st.session_state
        .portfolio_data
        is None
    ):
        st.info(
            "👈 Upload your portfolio "
            "from the sidebar to begin."
        )
        st.stop()
    # ========================================================
    # DATA
    # ========================================================
    portfolio = (
        st.session_state
        .portfolio_data
    )
    # ========================================================
    # COMMON CALCULATIONS
    # ========================================================
    try:
        total_investment = (
            calculate_total_investment(
                portfolio
            )
        )
    except Exception:
        total_investment = 0
    try:
        current_value = (
            calculate_current_value(
                portfolio
            )
        )
    except Exception:
        current_value = 0
    try:
        profit_loss = (
            calculate_profit_loss(
                portfolio
            )
        )
    except Exception:
        profit_loss = 0
    try:
        profit_loss_pct = (
            calculate_profit_loss_percentage(
                portfolio
            )
        )
    except Exception:
        profit_loss_pct = 0
    # ========================================================
    # NAVIGATION
    # ========================================================
    st.sidebar.divider()
    st.sidebar.subheader(
        "🧭 Sections"
    )
    section = st.sidebar.radio(
        "Go to",
        [
            "📈 Overview",
            "📊 Analytics",
            "🎯 Benchmark",
            "🤖 AI Insights",
            "📈 Stock Analysis",
            "📰 Market News",
            "💬 Ask AI",
        ],
    )
    # ========================================================
    # OVERVIEW
    # ========================================================
    if section == "📈 Overview":

        st.header(
            "📈 Portfolio Overview"
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                "💰 Total Investment",
                f"₹ {total_investment:,.2f}",
            )
        with col2:
            st.metric(
                "📊 Current Value",
                f"₹ {current_value:,.2f}",
            )
        with col3:
            st.metric(
                "💹 Profit / Loss",
                f"₹ {profit_loss:,.2f}",
            )
        with col4:
            st.metric(
                "📈 Return",
                f"{profit_loss_pct:.2f}%",
            )
        st.divider()
        left, right = st.columns(2)
        with left:
            st.subheader(
                "Investment vs Current Value"
            )
            chart_df = pd.DataFrame(
                {
                    "Type": [
                        "Investment",
                        "Current Value",
                    ],
                    "Value": [
                        float(total_investment or 0),
                        float(current_value or 0),
                    ],
                }
            )
            fig = px.bar(
                chart_df,
                x="Type",
                y="Value",
                text="Value",
            )
            fig.update_traces(
                texttemplate="₹%{text:,.0f}",
                textposition="outside",
            )
            fig.update_layout(
                yaxis_title="Value (₹)",
                xaxis_title="",
                height=380,
            )
            safe_plotly_chart(fig)
        with right:
            st.subheader(
                "Portfolio Holdings"
            )
            st.dataframe(
                portfolio,
                use_container_width=True,
                hide_index=True,
            )
    # ========================================================
    # ANALYTICS
    # ========================================================
    elif section == "📊 Analytics":
        st.header(
            "📊 Portfolio Analytics"
        )
        try:
            summary = calculate_portfolio_summary(
                portfolio
            )
        except Exception:
            summary = {}
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Total Value",
                f"₹ {summary.get('total_value', current_value):,.2f}",
            )
        with col2:
            st.metric(
                "Profit / Loss",
                f"₹ {summary.get('profit_loss', profit_loss):,.2f}",
            )
        with col3:
            st.metric(
                "Risk Score",
                f"{summary.get('risk_score', 0):.1f} / 10",
            )
        st.divider()
        # ----------------------------------------------------
        # SECTOR ALLOCATION + DAILY MOVERS
        # ----------------------------------------------------
        left, right = st.columns(2)
        with left:
            st.subheader(
                "🥧 Sector Allocation"
            )
            try:
                sector_data = compute_sector_breakdown(
                    portfolio
                )
            except Exception:
                sector_data = {}
            if sector_data:
                sector_df = pd.DataFrame(
                    [
                        {
                            "Sector": sector,
                            "Value": data.get("value", 0),
                            "Portfolio %": data.get(
                                "pct_of_portfolio",
                                0,
                            ),
                        }
                        for sector, data in sector_data.items()
                    ]
                )
                sector_df["Value"] = to_numeric_series(
                    sector_df["Value"]
                ).fillna(0)
                sector_df = sector_df[
                    sector_df["Value"] > 0
                ]
                if not sector_df.empty:
                    fig = px.pie(
                        sector_df,
                        names="Sector",
                        values="Value",
                        hole=0.5,
                    )
                    fig.update_layout(
                        height=380,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02,
                        ),
                    )
                    safe_plotly_chart(fig)
                else:
                    st.info(
                        "Sector values are unavailable."
                    )
            else:
                st.info(
                    "Sector information unavailable."
                )
        with right:
            st.subheader(
                "📈 Daily Movers"
            )
            if (
                "Stock Symbol" in portfolio.columns
                and "Change %" in portfolio.columns
            ):
                mover_df = portfolio[
                    ["Stock Symbol", "Change %"]
                ].copy()

                mover_df["Change %"] = to_numeric_series(
                    mover_df["Change %"]
                )
                mover_df = (
                    mover_df
                    .dropna(subset=["Change %"])
                    .drop_duplicates(
                        subset="Stock Symbol",
                        keep="first",
                    )
                    .sort_values(
                        "Change %",
                        ascending=False,
                    )
                )
                if not mover_df.empty:
                    fig = px.bar(
                        mover_df,
                        x="Stock Symbol",
                        y="Change %",
                        text="Change %",
                    )
                    fig.update_traces(
                        texttemplate="%{text:.2f}%",
                        textposition="outside",
                    )
                    fig.update_layout(
                        height=380,
                        xaxis_title="",
                        yaxis_title="Change %",
                    )
                    safe_plotly_chart(fig)
                else:
                    st.info(
                        "Daily change data unavailable."
                    )
            else:
                st.info(
                    "Daily change data unavailable."
                )
        # ----------------------------------------------------
        # TOP GAINERS / LOSERS
        # ----------------------------------------------------
        st.divider()
        st.subheader(
            "🏆 Top Gainers & Losers"
        )
        if (
            "Stock Symbol" in portfolio.columns
            and "Change %" in portfolio.columns
        ):
            mover_data = portfolio[
                ["Stock Symbol", "Change %"]
            ].copy()
            mover_data["Change %"] = to_numeric_series(
                mover_data["Change %"]
            )
            mover_data = (
                mover_data
                .dropna(subset=["Change %"])
                .drop_duplicates(
                    subset="Stock Symbol",
                    keep="first",
                )
            )
            top_gainers = (
                mover_data
                .sort_values(
                    "Change %",
                    ascending=False,
                )
                .head(5)
            )
            top_losers = (
                mover_data
                .sort_values(
                    "Change %",
                    ascending=True,
                )
                .head(5)
            )
            gain_col, loss_col = st.columns(2)
            with gain_col:
                st.markdown(
                    "### 🟢 Top Gainers"
                )
                if not top_gainers.empty:
                    fig = px.bar(
                        top_gainers,
                        x="Stock Symbol",
                        y="Change %",
                        text="Change %",
                    )
                    fig.update_traces(
                        texttemplate="%{text:.2f}%",
                        textposition="outside",
                    )
                    fig.update_layout(
                        height=350,
                        xaxis_title="",
                        yaxis_title="Change %",
                    )
                    safe_plotly_chart(fig)
                else:
                    st.info(
                        "No gainers available."
                    )
            with loss_col:
                st.markdown(
                    "### 🔴 Top Losers"
                )
                if not top_losers.empty:
                    fig = px.bar(
                        top_losers,
                        x="Stock Symbol",
                        y="Change %",
                        text="Change %",
                    )

                    fig.update_traces(
                        texttemplate="%{text:.2f}%",
                        textposition="outside",
                    )

                    fig.update_layout(
                        height=350,
                        xaxis_title="",
                        yaxis_title="Change %",
                    )

                    safe_plotly_chart(fig)
                else:
                    st.info(
                        "No losers available."
                    )

        # ----------------------------------------------------
        # STOCK-WISE P&L
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "💹 Stock-wise Profit / Loss"
        )

        required_pnl_columns = [
            "Stock Symbol",
            "Average Price",
            "Current Price",
            "Quantity",
        ]

        if all(
            column in portfolio.columns
            for column in required_pnl_columns
        ):
            pnl_df = portfolio[
                required_pnl_columns
            ].copy()

            pnl_df["Average Price"] = to_numeric_series(
                pnl_df["Average Price"]
            )

            pnl_df["Current Price"] = to_numeric_series(
                pnl_df["Current Price"]
            )

            pnl_df["Quantity"] = to_numeric_series(
                pnl_df["Quantity"]
            )

            pnl_df["Current Price"] = (
                pnl_df["Current Price"]
                .fillna(pnl_df["Average Price"])
            )

            pnl_df["Investment"] = (
                pnl_df["Average Price"]
                * pnl_df["Quantity"]
            )

            pnl_df["Current Value"] = (
                pnl_df["Current Price"]
                * pnl_df["Quantity"]
            )

            pnl_df["Profit / Loss"] = (
                pnl_df["Current Value"]
                - pnl_df["Investment"]
            )

            pnl_df = (
                pnl_df
                .groupby(
                    "Stock Symbol",
                    as_index=False,
                )
                .agg(
                    {
                        "Investment": "sum",
                        "Current Value": "sum",
                        "Profit / Loss": "sum",
                    }
                )
            )

            if not pnl_df.empty:
                fig = px.bar(
                    pnl_df,
                    x="Stock Symbol",
                    y="Profit / Loss",
                    text="Profit / Loss",
                )

                fig.update_traces(
                    texttemplate="₹%{text:,.0f}",
                    textposition="outside",
                )

                fig.update_layout(
                    height=400,
                    xaxis_title="",
                    yaxis_title="P&L (₹)",
                )

                safe_plotly_chart(fig)
            else:
                st.info(
                    "P&L data unavailable."
                )
        else:
            st.info(
                "Required columns for P&L analysis are unavailable."
            )

        # ----------------------------------------------------
        # PORTFOLIO PERFORMANCE OVER TIME
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "📈 Portfolio Performance Over Time"
        )

        period_option = st.selectbox(
            "Select Time Range",
            [
                "1 Month",
                "3 Months",
                "6 Months",
                "1 Year",
            ],
            key="performance_period",
        )

        period_mapping = {
            "1 Month": "1mo",
            "3 Months": "3mo",
            "6 Months": "6mo",
            "1 Year": "1y",
        }

        selected_period = period_mapping[
            period_option
        ]

        if (
            "Stock Symbol" in portfolio.columns
            and "Quantity" in portfolio.columns
        ):
            historical_symbols = (
                portfolio["Stock Symbol"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

            with st.spinner(
                "Loading historical portfolio data..."
            ):
                historical_df = get_historical_data(
                    historical_symbols,
                    selected_period,
                )

            if not historical_df.empty:
                quantity_df = portfolio[
                    ["Stock Symbol", "Quantity"]
                ].copy()

                quantity_df["Quantity"] = to_numeric_series(
                    quantity_df["Quantity"]
                ).fillna(0)

                quantity_map = (
                    quantity_df
                    .groupby("Stock Symbol")["Quantity"]
                    .sum()
                    .to_dict()
                )

                historical_df["Quantity"] = (
                    historical_df["Stock Symbol"]
                    .map(quantity_map)
                    .fillna(0)
                )

                historical_df["Portfolio Value"] = (
                    historical_df["Close"]
                    * historical_df["Quantity"]
                )

                performance_df = (
                    historical_df
                    .groupby("Date")["Portfolio Value"]
                    .sum()
                    .reset_index()
                )

                performance_df["Date"] = pd.to_datetime(
                    performance_df["Date"]
                ).dt.tz_localize(None)

                fig = px.line(
                    performance_df,
                    x="Date",
                    y="Portfolio Value",
                    title="Portfolio Value Over Time",
                )

                fig.update_layout(
                    height=450,
                    xaxis_title="Date",
                    yaxis_title="Portfolio Value (₹)",
                    hovermode="x unified",
                )

                safe_plotly_chart(fig)
            else:
                st.warning(
                    "Historical portfolio data is currently unavailable."
                )


    # ========================================================
    # BENCHMARK
    # ========================================================

    elif section == "🎯 Benchmark":

        st.header(
            "🎯 Benchmark Comparison"
        )

        st.subheader(
            "Portfolio vs Nifty 50"
        )

        benchmark_data = get_market_data(
            ["^NSEI"]
        )

        benchmark = benchmark_data.get(
            "^NSEI",
            {},
        )

        benchmark_change = benchmark.get(
            "change_pct"
        )

        if benchmark_change is not None:
            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Portfolio Return",
                    f"{profit_loss_pct:+.2f}%",
                )

            with col2:
                st.metric(
                    "Nifty 50 Daily Change",
                    f"{benchmark_change:+.2f}%",
                )

            benchmark_df = pd.DataFrame(
                {
                    "Asset": [
                        "My Portfolio",
                        "Nifty 50",
                    ],
                    "Return (%)": [
                        float(profit_loss_pct or 0),
                        float(benchmark_change or 0),
                    ],
                }
            )

            fig = px.bar(
                benchmark_df,
                x="Asset",
                y="Return (%)",
                text="Return (%)",
                title="Portfolio vs Nifty 50",
            )

            fig.update_traces(
                texttemplate="%{text:.2f}%",
                textposition="outside",
            )

            fig.update_layout(
                height=400,
                yaxis_title="Return (%)",
                xaxis_title="",
            )

            safe_plotly_chart(fig)
        else:
            st.warning(
                "Nifty 50 benchmark data is currently unavailable."
            )

        # ----------------------------------------------------
        # HISTORICAL BENCHMARK
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "📈 Historical Benchmark Comparison"
        )

        benchmark_period = st.selectbox(
            "Select Benchmark Period",
            [
                "1 Month",
                "3 Months",
                "6 Months",
                "1 Year",
            ],
            key="benchmark_period",
        )

        benchmark_period_mapping = {
            "1 Month": "1mo",
            "3 Months": "3mo",
            "6 Months": "6mo",
            "1 Year": "1y",
        }

        try:
            benchmark_history = yf.Ticker(
                "^NSEI"
            ).history(
                period=benchmark_period_mapping[
                    benchmark_period
                ],
                auto_adjust=False,
            )

            if not benchmark_history.empty:
                benchmark_history = (
                    benchmark_history
                    .reset_index()
                )

                benchmark_history["Date"] = (
                    pd.to_datetime(
                        benchmark_history["Date"]
                    ).dt.tz_localize(None)
                )

                first_value = benchmark_history[
                    "Close"
                ].iloc[0]

                benchmark_history[
                    "Nifty Return %"
                ] = (
                    (
                        benchmark_history["Close"]
                        / first_value
                    ) - 1
                ) * 100

                fig = px.line(
                    benchmark_history,
                    x="Date",
                    y="Nifty Return %",
                    title="Nifty 50 Performance",
                )

                fig.update_layout(
                    height=450,
                    xaxis_title="Date",
                    yaxis_title="Return (%)",
                    hovermode="x unified",
                )

                safe_plotly_chart(fig)
            else:
                st.warning(
                    "Historical Nifty 50 data unavailable."
                )

        except Exception as error:
            st.warning(
                f"Unable to load historical Nifty data: {error}"
            )


    # ========================================================
    # AI INSIGHTS - DIRECT AI CALLS
    # ========================================================

    elif section == "🤖 AI Insights":

        st.header(
            "🤖 AI Portfolio Insights"
        )

        st.caption(
            "AI insights are generated directly from the uploaded "
            "portfolio. No separate FastAPI process is required "
            "for the deployed Streamlit interface."
        )

        with st.expander(
            "🩺 Portfolio Health Score",
            expanded=True,
        ):
            if st.button(
                "Generate Health Score",
                key="health_score_button",
            ):
                try:
                    with st.spinner(
                        "Analyzing portfolio health..."
                    ):
                        result = portfolio_health_score(
                            portfolio
                        )

                    st.session_state.health_result = result

                except Exception as error:
                    st.error(
                        f"Health analysis failed: {error}"
                    )

            if st.session_state.health_result:
                st.markdown(
                    st.session_state.health_result
                )

        with st.expander(
            "⚠️ AI Risk Analysis"
        ):
            if st.button(
                "Generate Risk Analysis",
                key="risk_button",
            ):
                try:
                    with st.spinner(
                        "Analyzing portfolio risk..."
                    ):
                        result = portfolio_risk_analysis(
                            portfolio
                        )

                    st.session_state.risk_result = result

                except Exception as error:
                    st.error(
                        f"Risk analysis failed: {error}"
                    )

            if st.session_state.risk_result:
                st.markdown(
                    st.session_state.risk_result
                )

        with st.expander(
            "📋 AI Portfolio Summary"
        ):
            if st.button(
                "Generate Summary",
                key="summary_button",
            ):
                try:
                    with st.spinner(
                        "Generating portfolio summary..."
                    ):
                        result = generate_portfolio_summary(
                            portfolio
                        )

                    st.session_state.summary_result = result

                except Exception as error:
                    st.error(
                        f"Summary generation failed: {error}"
                    )

            if st.session_state.summary_result:
                st.markdown(
                    st.session_state.summary_result
                )

        with st.expander(
            "💡 Improvement Suggestions"
        ):
            if st.button(
                "Generate Suggestions",
                key="improvement_button",
            ):
                try:
                    with st.spinner(
                        "Generating suggestions..."
                    ):
                        result = portfolio_improvement_suggestions(
                            portfolio
                        )

                    st.session_state.improvement_result = result

                except Exception as error:
                    st.error(
                        f"Suggestion generation failed: {error}"
                    )

            if st.session_state.improvement_result:
                st.markdown(
                    st.session_state.improvement_result
                )


    # ========================================================
    # STOCK ANALYSIS
    # ========================================================

    elif section == "📈 Stock Analysis":

        st.header(
            "📈 Stock Analysis"
        )

        if "Stock Symbol" not in portfolio.columns:
            st.error(
                "Stock Symbol column is not available in portfolio."
            )
            st.stop()

        stocks = (
            portfolio["Stock Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        if not stocks:
            st.warning(
                "No stock symbols found."
            )
            st.stop()

        selected_stock = st.selectbox(
            "Select Stock",
            stocks,
        )

        # ----------------------------------------------------
        # STOCK PRICE HISTORY
        # ----------------------------------------------------

        st.subheader(
            "📈 Stock Price History"
        )

        chart_period = st.radio(
            "Time Range",
            [
                "1M",
                "3M",
                "6M",
                "1Y",
            ],
            horizontal=True,
            key="stock_chart_period",
        )

        period_map = {
            "1M": "1mo",
            "3M": "3mo",
            "6M": "6mo",
            "1Y": "1y",
        }

        with st.spinner(
            "Loading price history..."
        ):
            history = get_historical_data(
                [selected_stock],
                period_map[chart_period],
            )

        if not history.empty:
            history["Date"] = pd.to_datetime(
                history["Date"]
            ).dt.tz_localize(None)

            fig = px.line(
                history,
                x="Date",
                y="Close",
                title=f"{selected_stock} Price History",
                markers=False,
            )

            fig.update_layout(
                height=450,
                xaxis_title="Date",
                yaxis_title="Price (₹)",
                hovermode="x unified",
            )

            safe_plotly_chart(fig)
        else:
            st.warning(
                "Historical price data unavailable."
            )

        # ----------------------------------------------------
        # STOCK INFO
        # ----------------------------------------------------

        with st.spinner(
            "Loading stock information..."
        ):
            try:
                stock_info = get_stock_info(
                    selected_stock
                )
            except Exception as error:
                stock_info = {}
                st.warning(
                    f"Unable to load stock information: {error}"
                )

        # ----------------------------------------------------
        # STOCK KPI
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            current_price_info = stock_info.get(
                "Current Price"
            )

            st.metric(
                "Current Price",
                (
                    f"₹ {current_price_info:,.2f}"
                    if isinstance(
                        current_price_info,
                        (int, float),
                    )
                    else "N/A"
                ),
            )

        with col2:
            st.metric(
                "P/E Ratio",
                stock_info.get(
                    "PE Ratio",
                    "N/A",
                ),
            )

        with col3:
            st.metric(
                "52W High",
                stock_info.get(
                    "52 Week High",
                    "N/A",
                ),
            )

        with col4:
            st.metric(
                "52W Low",
                stock_info.get(
                    "52 Week Low",
                    "N/A",
                ),
            )

        st.divider()

        # ----------------------------------------------------
        # COMPANY INFORMATION + PORTFOLIO POSITION
        # ----------------------------------------------------

        left, right = st.columns(2)

        with left:
            st.subheader(
                "🏢 Company Information"
            )

            st.write(
                f"**Company:** "
                f"{stock_info.get('Company name', 'N/A')}"
            )

            st.write(
                f"**Sector:** "
                f"{stock_info.get('sector', 'N/A')}"
            )

            st.write(
                f"**Industry:** "
                f"{stock_info.get('Industry', 'N/A')}"
            )

            st.write(
                f"**Market Cap:** "
                f"{stock_info.get('Market Cap', 'N/A')}"
            )

        with right:
            st.subheader(
                "📊 Portfolio Position"
            )

            selected_df = portfolio[
                portfolio["Stock Symbol"]
                .astype(str)
                .str.strip()
                == selected_stock
            ]

            st.dataframe(
                selected_df,
                use_container_width=True,
                hide_index=True,
            )


    # ========================================================
    # MARKET NEWS
    # ========================================================

    elif section == "📰 Market News":

        st.header(
            "📰 Latest Market News"
        )

        stocks = (
            portfolio["Stock Symbol"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        selected_stock = (
            st.selectbox(
                "Select Stock",
                stocks,
                key="news_stock",
            )
        )

        if st.button(
            "Fetch Latest News",
            key="fetch_news_button",
        ):

            try:

                articles = (
                    get_stock_news(
                        selected_stock
                    )
                )

                (
                    st.session_state
                    .news_data[
                        selected_stock
                    ]
                ) = articles

            except Exception as error:

                st.error(
                    f"News error: {error}"
                )

        articles = (
            st.session_state
            .news_data
            .get(
                selected_stock,
                [],
            )
        )

        for article in articles:

            st.markdown(
                "### "
                + article.get(
                    "Title",
                    article.get(
                        "title",
                        "News",
                    ),
                )
            )

            st.write(
                article.get(
                    "Description",
                    article.get(
                        "description",
                        "",
                    ),
                )
            )

    # ========================================================
    # ASK AI - DIRECT HYBRID CHAT
    # Portfolio + RAG + Tools + News
    # ========================================================

    elif section == "💬 Ask AI":

        st.header(
            "💬 Ask AI"
        )

        st.caption(
            "Ask questions about your uploaded portfolio, stocks "
            "and financial concepts. The assistant uses portfolio "
            "data, FAISS RAG knowledge and the project AI tools."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.success(
                "📊 Portfolio context: Available"
            )

        with col2:
            st.success(
                "📚 FAISS RAG knowledge: Enabled"
            )

        question = st.text_area(
            "Your Question",
            placeholder=(
                "Examples:\n"
                "Which stock has the highest current value?\n"
                "What is P/E ratio?\n"
                "Explain concentration risk based on my portfolio."
            ),
            height=130,
            key="hybrid_question",
        )

        if st.button(
            "🤖 Ask AI",
            type="primary",
            key="hybrid_ask_button",
            width="stretch",
        ):

            if not question.strip():
                st.warning(
                    "Please enter a question."
                )

            else:
                try:
                    portfolio_records = prepare_portfolio_payload(
                        portfolio
                    )

                    ai_news_data = prepare_news_payload(
                        st.session_state.news_data
                    )

                    with st.spinner(
                        "AI is analyzing your portfolio "
                        "and financial knowledge..."
                    ):
                        answer = run_chat_chain(
                            user_question=question.strip(),
                            portfolio_data=portfolio_records,
                            news_data=ai_news_data,
                        )

                    st.session_state.chat_answer = answer

                except Exception as error:
                    st.error(
                        f"AI Chat failed: {error}"
                    )

        if st.session_state.chat_answer:

            st.divider()

            st.subheader(
                "🤖 AI Answer"
            )

            st.markdown(
                st.session_state.chat_answer
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
