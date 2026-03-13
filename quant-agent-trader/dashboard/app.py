"""
Streamlit Dashboard - Real-time visualization of the trading system.

Usage:
    streamlit run dashboard/app.py

    # Or run directly
    python -m dashboard.app
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import json
import os
import sys
import csv
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def get_holdings_dir() -> str:
    """Get holdings directory from config."""
    return os.getenv("HOLDINGS_DIR", "C:\\Users\\Harshil\\Desktop\\holdings")


def load_holdings_from_csv() -> List[Dict]:
    """
    Load holdings directly from the configured directory.
    Reads all CSV files in the holdings directory.
    """
    holdings_dir = get_holdings_dir()

    if not os.path.exists(holdings_dir):
        return []

    # Find CSV files
    csv_files = []
    for f in os.listdir(holdings_dir):
        if f.endswith(".csv"):
            csv_files.append(os.path.join(holdings_dir, f))

    if not csv_files:
        return []

    # Merge holdings from all CSV files (latest values for duplicates)
    holdings = {}

    for csv_path in csv_files:
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get("Instrument", "").strip()
                    qty = row.get("Qty.", "").strip()
                    avg_cost = row.get("Avg. cost", "").strip()
                    ltp = row.get("LTP", "").strip()

                    if not symbol or not qty or qty == "0":
                        continue

                    try:
                        holdings[symbol] = {
                            "Symbol": symbol,
                            "Qty": int(float(qty.replace(",", ""))),
                            "Entry": float(avg_cost.replace(",", "")),
                            "LTP": float(ltp.replace(",", "")),
                        }
                    except (ValueError, KeyError):
                        continue
        except Exception as e:
            print(f"Error reading {csv_path}: {e}")
            continue

    return list(holdings.values())


def get_upstox_live_price(symbol: str) -> Optional[float]:
    """Get live price from Upstox API."""
    access_token = os.getenv("UPSTOX_ACCESS_TOKEN", "")

    if not access_token:
        return None

    try:
        # Instrument key mapping (add more as needed)
        instrument_keys = {
            "RELIANCE": "NSE_EQ|INE002A01018",
            "TCS": "NSE_EQ|INE467B01029",
            "HDFCBANK": "NSE_EQ|INE040A01034",
            "INFY": "NSE_EQ|INE009A01021",
            "AXISBANK": "NSE_EQ|INE238A01034",
            "ICICIBANK": "NSE_EQ|INE090A01021",
            "KOTAKBANK": "NSE_EQ|INE237A01028",
            "SBIN": "NSE_EQ|INE062A01020",
            "LT": "NSE_EQ|INE018A01030",
            "TITAN": "NSE_EQ|INE280A01028",
            "BAJFINANCE": "NSE_EQ|INE238A01034",
            "ONGC": "NSE_EQ|INE213A01029",
        }

        instrument = instrument_keys.get(symbol.upper())
        if not instrument:
            return None

        import requests

        url = "https://api.upstox.com/v3/market-quote/ltp"
        params = {"instrument_key": instrument}
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            for key, value in data.get("data", {}).items():
                if value.get("last_price"):
                    return value.get("last_price")
        return None
    except Exception as e:
        return None


def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def main():
    st.set_page_config(page_title="Quant Agent Trader", page_icon="📈", layout="wide")

    # The page will now auto refresh every 10 minutes.
    st_autorefresh(interval=600000, key="datarefresh")

    st.title("📈 Quant Agent Trader Dashboard")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Overview", "Signals", "Portfolio", "Backtest", "Agents"]
    )

    with tab1:
        show_overview()

    with tab2:
        show_signals()

    with tab3:
        show_portfolio()

    with tab4:
        show_backtest()

    with tab5:
        show_agents()


def show_overview():
    """Show system overview with holdings and signals."""

    # Load portfolio data directly from CSV files in holdings directory
    portfolio = load_holdings_from_csv()

    # Get live prices from Upstox for holdings
    if portfolio:
        for pos in portfolio:
            live_price = get_upstox_live_price(pos["Symbol"])
            if live_price:
                pos["LTP"] = live_price

    # Calculate metrics
    if portfolio:
        df_port = pd.DataFrame(portfolio)
        total_value = (df_port["LTP"] * df_port["Qty"]).sum()
        total_invested = (df_port["Entry"] * df_port["Qty"]).sum()
        total_pnl = total_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        active_positions = len(portfolio)
    else:
        total_value = 0
        total_pnl = 0
        total_pnl_pct = 0
        active_positions = 0

    # Try to load cached signals if available (from run_holdings_analysis)
    holdings_signals = load_json("holdings_signals.json")

    # Calculate signal stats
    if holdings_signals:
        total_signals = len(holdings_signals)
        buy_signals = sum(
            1 for s in holdings_signals if s.get("decision", "").upper() == "BUY"
        )
        sell_signals = sum(
            1 for s in holdings_signals if s.get("decision", "").upper() == "SELL"
        )
        hold_signals = sum(
            1 for s in holdings_signals if s.get("decision", "").upper() == "HOLD"
        )
        avg_confidence = (
            sum(s.get("confidence", 0) for s in holdings_signals) / total_signals
            if total_signals > 0
            else 0
        )
    else:
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        avg_confidence = 0

    # Try to load market regime
    market_regime = load_json("market_regime.json")
    regime = market_regime.get("regime", "Unknown") if market_regime else "Unknown"
    regime_emoji = {"bull": "↗", "bear": "↘", "normal": "→", "volatile": "↕"}.get(
        regime.lower(), "→"
    )

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Active Positions", str(active_positions))

    with col2:
        pnl_emoji = "+" if total_pnl >= 0 else ""
        st.metric(
            "Total P&L", f"Rs.{total_pnl:,.0f}", f"{pnl_emoji}{total_pnl_pct:.1f}%"
        )

    with col3:
        st.metric("Avg Signal Confidence", f"{avg_confidence:.1f}%")

    with col4:
        st.metric("Market Regime", regime.title(), regime_emoji)

    st.divider()

    # Holdings table
    if portfolio:
        st.subheader("Your Holdings")

        df_holdings = pd.DataFrame(portfolio)

        # Calculate P&L for each position
        df_holdings["P&L"] = (df_holdings["LTP"] - df_holdings["Entry"]) * df_holdings[
            "Qty"
        ]
        df_holdings["P&L%"] = (
            (df_holdings["LTP"] - df_holdings["Entry"]) / df_holdings["Entry"] * 100
        )

        # Add signal if available
        if holdings_signals:
            signals_dict = {s["symbol"]: s for s in holdings_signals}
            df_holdings["Signal"] = df_holdings["Symbol"].map(
                lambda x: signals_dict.get(x, {}).get("decision", "N/A")
            )
            df_holdings["Confidence"] = df_holdings["Symbol"].map(
                lambda x: signals_dict.get(x, {}).get("confidence", 0)
            )

        def color_pnl(val):
            if val > 0:
                return "color:green"
            if val < 0:
                return "color:red"
            return ""

        st.dataframe(
            df_holdings.style.map(color_pnl, subset=["P&L"]),
            column_config={
                "P&L": st.column_config.NumberColumn("P&L", format="Rs.%.0f"),
                "P&L%": st.column_config.NumberColumn("P&L%", format="%.1f%%"),
                "Confidence": st.column_config.ProgressColumn(
                    "Confidence", format="%.0f%%", min_value=0, max_value=100
                ),
            },
            use_container_width=True,
        )

        # Signal distribution
        if holdings_signals:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Signal Distribution")
                signal_dist = {
                    "BUY": buy_signals,
                    "HOLD": hold_signals,
                    "SELL": sell_signals,
                }
                st.bar_chart(pd.Series(signal_dist))

            with col2:
                st.subheader("Portfolio Allocation")
                df_holdings["Value"] = df_holdings["LTP"] * df_holdings["Qty"]
                top_holdings = df_holdings.nlargest(10, "Value")[["Symbol", "Value"]]
                top_holdings = top_holdings.set_index("Symbol")["Value"]
                st.bar_chart(top_holdings)
    else:
        holdings_dir = get_holdings_dir()
        st.warning(f"No holdings found in: {holdings_dir}")
        st.markdown(f"""
        **To add your holdings:**
        1. Export holdings from your broker (Zerodha/Upstox)
        2. Save CSV files to: `{holdings_dir}`
        3. Expected CSV columns: Instrument, Qty., Avg. cost, LTP
        """)

    st.divider()

    # Quick actions
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Equity Curve")
        equity_df = load_csv("equity_curve.csv")
        if equity_df is not None:
            equity_df["date"] = pd.to_datetime(equity_df["date"])
            st.line_chart(equity_df.set_index("date")["equity"])
        else:
            st.info("Run backtest to generate equity curve")

    with col2:
        st.subheader("Quick Actions")

        if st.button("Run Holdings Analysis"):
            st.info("Run: python -m data.run_holdings_analysis")

        if st.button("Refresh Data"):
            st.rerun()

    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Equity Curve")

        equity_df = load_csv("equity_curve.csv")

        if equity_df is not None:
            equity_df["date"] = pd.to_datetime(equity_df["date"])
            st.line_chart(equity_df.set_index("date")["equity"])
        else:
            st.warning("No equity curve data available")

    with col2:
        st.subheader("Quick Actions")

        if st.button("Run Holdings Analysis"):
            st.info("Run: python -m data.run_holdings_analysis")

        if st.button("Refresh Data"):
            st.rerun()


def color_signal(val):
    if val == "BUY":
        return "color:green;font-weight:bold"
    if val == "SELL":
        return "color:red;font-weight:bold"
    return "color:orange"


def show_signals():
    """Show signal analysis."""
    st.subheader("Signal Analysis")

    col1, col2 = st.columns([1, 2])

    with col1:
        symbol = st.selectbox("Select Symbol", ["RELIANCE", "TCS", "HDFCBANK", "INFY"])
        regime = st.selectbox(
            "Market Regime", ["Bull", "Bear", "Sideways", "High Volatility"]
        )

    with col2:
        st.write("Current regime weights:")

        weights = {
            "Technical": 0.30,
            "Fundamental": 0.25,
            "Sentiment": 0.15,
            "Macro": 0.10,
            "Risk": 0.10,
            "Market Structure": 0.10,
        }

        st.bar_chart(pd.Series(weights))

    st.divider()

    st.subheader("Signal Breakdown")

    # signal_data = [
    #     {"Agent": "RSI", "Signal": "BUY", "Confidence": 75, "Score": 0.8},
    #     {"Agent": "MACD", "Signal": "BUY", "Confidence": 68, "Score": 0.6},
    #     {"Agent": "Momentum", "Signal": "HOLD", "Confidence": 55, "Score": 0.2},
    #     {"Agent": "Sentiment", "Signal": "BUY", "Confidence": 72, "Score": 0.7},
    #     {"Agent": "Volatility", "Signal": "SELL", "Confidence": 60, "Score": -0.5},
    # ]

    signal_data = load_json("signals.json")

    if signal_data is None:
        st.warning("No signals available")
        return

    df_signals = pd.DataFrame(signal_data)

    st.dataframe(
        df_signals.style.map(color_signal, subset=["Signal"]),
        column_config={
            "Signal": st.column_config.TextColumn("Signal"),
            "Confidence": st.column_config.ProgressColumn(
                "Confidence", format="%d%%", min_value=0, max_value=100
            ),
            "Score": st.column_config.NumberColumn("Score", format="%.2f"),
        },
        width="stretch",
    )

    st.subheader("Aggregated Signal")

    agg_col1, agg_col2, agg_col3 = st.columns(3)

    with agg_col1:
        st.metric("Final Score", "0.65")
    with agg_col2:
        st.metric("Decision", "BUY", "+0.15")
    with agg_col3:
        st.metric("Confidence", "72%")


def show_portfolio():
    """Show portfolio view."""
    st.subheader("Portfolio Positions")

    # Load holdings directly from CSV files
    positions = load_holdings_from_csv()

    # Get live prices from Upstox
    if positions:
        for pos in positions:
            live_price = get_upstox_live_price(pos["Symbol"])
            if live_price:
                pos["LTP"] = live_price

    if not positions:
        holdings_dir = get_holdings_dir()
        st.info("📥 No portfolio data loaded")
        st.markdown(f"""
        **To add your holdings:**
        1. Export holdings from your broker (Zerodha/Upstox) as CSV
        2. Save CSV files to: `{holdings_dir}`
        
        Expected CSV columns: Instrument, Qty., Avg. cost, LTP
        """)
        return

    df_port = pd.DataFrame(positions)

    # Calculate P&L columns
    df_port["P&L"] = (df_port["LTP"] - df_port["Entry"]) * df_port["Qty"]
    df_port["P&L%"] = (df_port["LTP"] - df_port["Entry"]) / df_port["Entry"] * 100

    def color_pnl(val):
        if val < 0:
            return "color:red"
        return "color:green"

    st.dataframe(df_port.style.map(color_pnl, subset=["P&L"]), use_container_width=True)

    # Calculate allocation from real data
    total_value = (df_port["LTP"] * df_port["Qty"]).sum()

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Allocation")

        # Calculate allocation from actual holdings
        df_port["Value"] = df_port["LTP"] * df_port["Qty"]
        df_port["Weight"] = (df_port["Value"] / total_value * 100).round(1)
        allocation = dict(zip(df_port["Symbol"], df_port["Weight"]))

        if len(allocation) > 0:
            st.bar_chart(pd.Series(allocation))
        else:
            st.warning("No positions to display")

    with col2:
        st.subheader("Risk Metrics")

        # Calculate metrics from real data
        total_invested = (df_port["Entry"] * df_port["Qty"]).sum()
        total_pnl_val = total_value - total_invested
        total_pnl_pct = (
            (total_pnl_val / total_invested * 100) if total_invested > 0 else 0
        )

        metrics = {
            "Portfolio Value": f"Rs.{total_value:,.0f}",
            "Total Invested": f"Rs.{total_invested:,.0f}",
            "Total P&L": f"Rs.{total_pnl_val:,.0f} ({total_pnl_pct:+.1f}%)",
        }

        for k, v in metrics.items():
            st.metric(k, v)


def show_backtest():
    """Show backtest results."""
    st.subheader("Backtest Results")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Return", "+145%", "+45%")
    with col2:
        st.metric("Sharpe Ratio", "1.82")
    with col3:
        st.metric("Max Drawdown", "-12%")
    with col4:
        st.metric("Win Rate", "58%")

    st.divider()

    st.subheader("Monthly Returns")

    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    returns = [2.5, 1.8, -1.2, 3.4, 2.1, -0.8, 4.2, 1.5, -2.1, 3.8, 2.2, 1.1]

    chart_data = pd.DataFrame({"Month": months, "Return": returns})

    st.bar_chart(chart_data.set_index("Month"))

    st.divider()

    st.subheader("Drawdown Chart")

    dates = pd.date_range(start=datetime.now() - timedelta(days=90), periods=90)
    drawdown = -np.cumsum(np.maximum(0, -np.random.randn(90) * 0.5))

    dd_data = pd.DataFrame({"date": dates, "drawdown": drawdown})

    st.line_chart(dd_data.set_index("date"))


def show_agents():
    """Show agent performance."""
    st.subheader("Agent Performance")

    # agent_data = [
    #     {"Category": "Technical", "Agents": 18, "Avg Accuracy": 0.62, "Signal %": 45},
    #     {"Category": "Fundamental", "Agents": 8, "Avg Accuracy": 0.58, "Signal %": 25},
    #     {"Category": "Sentiment", "Agents": 4, "Avg Accuracy": 0.55, "Signal %": 15},
    #     {"Category": "Macro", "Agents": 6, "Avg Accuracy": 0.52, "Signal %": 10},
    #     {"Category": "Risk", "Agents": 5, "Avg Accuracy": 0.48, "Signal %": 5},
    # ]
    agent_data = load_json("agents.json")

    if agent_data is None:
        st.warning("No agent metrics available")
        return

    df_agents = pd.DataFrame(agent_data)

    st.dataframe(
        df_agents,
        column_config={
            "Avg Accuracy": st.column_config.ProgressColumn(
                "Accuracy", format="%.0f%%", min_value=0, max_value=1
            ),
        },
        width="stretch",
    )

    st.divider()

    st.subheader("Feature Importance")

    importance = [
        {"Feature": "mean_reversion_score", "Importance": 0.21},
        {"Feature": "rsi_score", "Importance": 0.17},
        {"Feature": "sentiment_score", "Importance": 0.14},
        {"Feature": "macd_score", "Importance": 0.11},
        {"Feature": "momentum_score", "Importance": 0.09},
        {"Feature": "volatility_score", "Importance": 0.08},
        {"Feature": "macro_score", "Importance": 0.06},
    ]

    df_imp = pd.DataFrame(importance)

    st.bar_chart(df_imp.set_index("Feature"))


def show_experiment_tracker():
    """Show experiment tracking."""
    st.subheader("Experiments")

    experiments = [
        {
            "ID": "exp_001",
            "Strategy": "Momentum",
            "Sharpe": 1.82,
            "Drawdown": "-12%",
            "Status": "Completed",
        },
        {
            "ID": "exp_002",
            "Strategy": "Mean Reversion",
            "Sharpe": 1.45,
            "Drawdown": "-8%",
            "Status": "Completed",
        },
        {
            "ID": "exp_003",
            "Strategy": "ML Meta",
            "Sharpe": 2.15,
            "Drawdown": "-10%",
            "Status": "Running",
        },
    ]

    df_exp = pd.DataFrame(experiments)

    st.dataframe(df_exp, width="stretch")


def show_live_trading():
    """Show live trading view."""
    st.subheader("Live Trading")

    trades = load_json("trades.json")

    if trades is None:
        st.info("📥 No trade history loaded")
        st.markdown("""
        **To import your trades:**
        1. Export holdings from your broker as CSV
        2. Run: `python -m data.import_portfolio <path_to_csv>`
        
        Trade history will be generated from your holdings import.
        """)
        return

    col1, col2 = st.columns(2)

    with col1:
        st.info("📊 Trade History Loaded")
        st.write(f"Total trades: {len(trades)}")

    with col2:
        # Show last trade time
        if trades:
            last_trade = trades[0].get("Time", "N/A")
            st.write(f"Last trade: {last_trade}")

    st.divider()

    st.subheader("Recent Trades")

    st.table(pd.DataFrame(trades))


if __name__ == "__main__":
    main()
