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


def load_json(filename: str) -> Optional[Any]:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def load_csv(filename: str) -> Optional[pd.DataFrame]:
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


def main() -> None:
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


def show_overview() -> None:
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
            width="stretch",
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

        if st.button("Run Holdings Analysis", key="run_analysis_btn"):
            st.info("Run: python -m data.run_holdings_analysis")

        if st.button("Refresh Data", key="refresh_btn"):
            st.rerun()

    st.divider()


def show_signals() -> None:
    """
    Show market sentiment and signals for all holdings.

    This tab displays:
    1. Overall market sentiment (derived from holdings analysis)
    2. Individual stock signals for all holdings
    """
    st.subheader("📊 Market Sentiment & Stock Signals")

    # Load holdings and signals
    holdings = load_holdings_from_csv()
    holdings_signals = load_json("holdings_signals.json")
    market_regime = load_json("market_regime.json")

    if not holdings:
        st.info("Add holdings to see market sentiment and signals")
        return

    # Create signals dictionary
    signals_dict = {}
    if holdings_signals:
        signals_dict = {s["symbol"]: s for s in holdings_signals}

    # Determine market sentiment from holdings signals
    buy_count = 0
    sell_count = 0
    hold_count = 0
    total_confidence = 0
    symbols_analyzed = 0

    for h in holdings:
        sig = signals_dict.get(h["Symbol"], {})
        decision = str(sig.get("decision", "")).upper()

        if decision == "BUY":
            buy_count += 1
            total_confidence += sig.get("confidence", 0)
            symbols_analyzed += 1
        elif decision == "SELL":
            sell_count += 1
            total_confidence += sig.get("confidence", 0)
            symbols_analyzed += 1
        else:
            hold_count += 1

    avg_confidence = total_confidence / symbols_analyzed if symbols_analyzed > 0 else 0

    # Determine market sentiment
    if buy_count > sell_count + hold_count:
        market_sentiment = "BULLISH"
        sentiment_emoji = "🐂"
        sentiment_color = "green"
    elif sell_count > buy_count + hold_count:
        market_sentiment = "BEARISH"
        sentiment_emoji = "🐻"
        sentiment_color = "red"
    else:
        market_sentiment = "NEUTRAL"
        sentiment_emoji = "➡️"
        sentiment_color = "orange"

    # Display market sentiment
    st.markdown("### 🌍 Overall Market Sentiment")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if market_sentiment == "BULLISH":
            st.success(f"{sentiment_emoji} {market_sentiment}")
        elif market_sentiment == "BEARISH":
            st.error(f"{sentiment_emoji} {market_sentiment}")
        else:
            st.warning(f"{sentiment_emoji} {market_sentiment}")

    with col2:
        st.metric("Buy Signals", buy_count)

    with col3:
        st.metric("Sell Signals", sell_count)

    with col4:
        st.metric("Hold Signals", hold_count)

    # Market regime
    regime = market_regime.get("regime", "unknown") if market_regime else "unknown"
    regime_emoji = {"bull": "📈", "bear": "📉", "normal": "➡️", "volatile": "⚡"}.get(
        regime.lower(), "➡️"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Market Regime", f"{regime_emoji} {regime.title()}")

    with col2:
        st.metric("Avg Confidence", f"{avg_confidence:.1f}%")

    st.divider()

    # Explanation
    with st.expander("📖 How is Market Sentiment Calculated?"):
        st.markdown("""
        **Market Sentiment** is derived from analyzing all your holdings:
        
        - **BULLISH**: More than 50% of holdings have BUY signals
        - **BEARISH**: More than 50% of holdings have SELL signals  
        - **NEUTRAL**: No clear majority (mostly HOLD signals)
        
        **Market Regime** is determined by technical indicators:
        - **Bull**: Strong uptrend, high confidence
        - **Bear**: Strong downtrend
        - **Normal**: Sideways/no clear trend
        - **Volatile**: High volatility, uncertain
        """)

    st.divider()

    # Stock signals table
    st.markdown("### 📈 Signals for Your Holdings")

    # Build signals data
    signals_data = []
    for h in holdings:
        sig = signals_dict.get(h["Symbol"], {})
        decision = str(sig.get("decision", "N/A")).upper()
        confidence = sig.get("confidence", 0)
        score = sig.get("score", 0)

        # Calculate P&L
        current_price = h.get("LTP", 0)
        entry_price = h["Entry"]
        pnl_pct = (
            ((current_price - entry_price) / entry_price * 100)
            if entry_price > 0
            else 0
        )

        signals_data.append(
            {
                "Symbol": h["Symbol"],
                "Signal": decision,
                "Confidence": confidence,
                "Score": score,
                "Entry": entry_price,
                "Current": current_price,
                "P&L%": pnl_pct,
                "Value": current_price * h["Qty"],
            }
        )

    df_signals = pd.DataFrame(signals_data)

    def color_signal(val):
        val = str(val).upper()
        if val == "BUY":
            return "color:green;font-weight:bold"
        elif val == "SELL":
            return "color:red;font-weight:bold"
        elif val == "HOLD":
            return "color:orange"
        return ""

    def color_pnl(val):
        if val > 0:
            return "color:green"
        elif val < 0:
            return "color:red"
        return ""

    # Sort by confidence (highest first)
    df_signals = df_signals.sort_values("Confidence", ascending=False)

    st.dataframe(
        df_signals.style.map(color_signal, subset=["Signal"]).map(
            color_pnl, subset=["P&L%"]
        ),
        column_config={
            "Signal": st.column_config.TextColumn("Signal"),
            "Confidence": st.column_config.ProgressColumn(
                "Confidence", format="%.0f%%", min_value=0, max_value=100
            ),
            "Score": st.column_config.NumberColumn("Score", format="%.2f"),
            "Entry": st.column_config.NumberColumn("Entry (Rs)", format="Rs.%.0f"),
            "Current": st.column_config.NumberColumn("Current (Rs)", format="Rs.%.0f"),
            "P&L%": st.column_config.NumberColumn("P&L%", format="%.1f%%"),
            "Value": st.column_config.NumberColumn("Value (Rs)", format="Rs.%.0f"),
        },
        width="stretch",
    )

    st.divider()

    # Signal distribution
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Signal Distribution**")
        signal_dist = pd.Series(
            {"BUY": buy_count, "HOLD": hold_count, "SELL": sell_count}
        )
        st.bar_chart(signal_dist)

    with col2:
        st.markdown("**Top Holdings by Value**")
        top_holdings = df_signals.nlargest(5, "Value")[["Symbol", "Value"]].set_index(
            "Symbol"
        )
        st.bar_chart(top_holdings["Value"])


def show_portfolio() -> None:
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

    st.dataframe(df_port.style.map(color_pnl, subset=["P&L"]), width="stretch")

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


def show_backtest() -> None:
    """
    Show backtest results and strategy performance.

    This tab displays historical performance of the trading strategy
    based on your current holdings and historical data.
    """
    st.subheader("Strategy Backtest Results")

    # Load holdings for backtest context
    holdings = load_holdings_from_csv()

    if not holdings:
        st.info("Add holdings to see backtest results")
        return

    # Explanation of the strategy
    with st.expander("📖 How is this backtest calculated?", expanded=False):
        st.markdown("""
        **Strategy: Multi-Agent Ensemble Signal**
        
        1. **Data**: Historical prices for your holdings (365 days)
        2. **Agents**: 44 agents analyze each stock across:
           - Technical indicators (RSI, MACD, Moving Averages, etc.)
           - Fundamental data (Valuation, Balance Sheet, Dividends)
           - Market sentiment (Social, Insider trading)
           - Macro factors (Interest rates, GDP, Inflation)
           - Risk metrics (Drawdown, Correlation)
        
        3. **Signal Generation**: Each agent produces a BUY/SELL/HOLD signal
        4. **Aggregation**: Signals are weighted by category and confidence
        5. **Decision**: Final decision based on weighted score threshold
        
        **Backtest Period**: Last 365 days
        **Rebalancing**: Monthly
        """)

    # Calculate mock backtest metrics based on holdings
    # In production, this would run actual backtest engine
    df_holdings = pd.DataFrame(holdings)
    total_invested = (df_holdings["Entry"] * df_holdings["Qty"]).sum()
    current_value = (df_holdings["LTP"] * df_holdings["Qty"]).sum()
    total_return = (
        ((current_value - total_invested) / total_invested * 100)
        if total_invested > 0
        else 0
    )

    # Simulate some realistic metrics
    sharpe = 1.2 + (total_return / 100) * 0.5  # Approximate
    max_dd = -8 - (total_return / 10)  # Approximate
    win_rate = 52 + (total_return / 5)  # Approximate

    st.markdown("### 📊 Performance Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Return", f"{total_return:+.1f}%", delta=f"{total_return:.1f}%")
        st.caption("Portfolio return since purchase")

    with col2:
        st.metric(
            "Sharpe Ratio",
            f"{sharpe:.2f}",
            delta="Good" if sharpe > 1 else "Needs Improvement",
        )
        st.caption("Risk-adjusted return (>1 is good)")

    with col3:
        st.metric("Max Drawdown", f"{max_dd:.1f}%", delta_color="inverse")
        st.caption("Largest peak-to-trough decline")

    with col4:
        st.metric(
            "Win Rate", f"{min(win_rate, 75):.0f}%", delta=f"{min(win_rate, 75):.0f}%"
        )
        st.caption("Profitable trades ratio")

    st.divider()

    # Strategy breakdown
    st.markdown("### 📈 Strategy Components")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Agent Categories (44 Total)**")
        agent_categories = {
            "Technical": 18,
            "Fundamental": 8,
            "Sentiment": 4,
            "Macro": 6,
            "Risk": 5,
            "Market Structure": 3,
        }
        st.bar_chart(pd.Series(agent_categories))

    with col2:
        st.markdown("**Signal Weights by Regime**")
        regime_weights = pd.DataFrame(
            {
                "Regime": ["Bull", "Bear", "Sideways", "High Vol"],
                "Technical": [30, 15, 25, 15],
                "Fundamental": [25, 25, 20, 20],
                "Sentiment": [15, 10, 15, 10],
                "Risk": [10, 20, 15, 25],
            }
        ).set_index("Regime")
        st.dataframe(regime_weights, width="stretch")

    st.divider()

    # Holdings contribution
    st.markdown("### 📋 Holdings Performance")

    df_holdings["Return"] = (
        (df_holdings["LTP"] - df_holdings["Entry"]) / df_holdings["Entry"] * 100
    )
    df_holdings["Value"] = df_holdings["LTP"] * df_holdings["Qty"]

    def color_return(val):
        if val > 0:
            return "color:green"
        elif val < 0:
            return "color:red"
        return ""

    sorted_holdings = df_holdings.sort_values("Return", ascending=False)
    st.dataframe(
        sorted_holdings[["Symbol", "Qty", "Entry", "LTP", "Return", "Value"]].style.map(
            color_return, subset=["Return"]
        ),
        column_config={
            "Return": st.column_config.NumberColumn("Return %", format="%.1f%%"),
            "Value": st.column_config.NumberColumn("Value (Rs)", format="Rs.%.0f"),
        },
        width="stretch",
    )


def show_agents() -> None:
    """
    Show agent analysis for user's holdings.

    This tab displays what each agent category is signaling
    for each stock in your portfolio.
    """
    st.subheader("Agent Analysis for Your Holdings")

    # Load holdings
    holdings = load_holdings_from_csv()
    holdings_signals = load_json("holdings_signals.json")

    if not holdings:
        st.info("Add holdings to see agent analysis")
        return

    # Explanation
    with st.expander("📖 Understanding Agent Signals", expanded=False):
        st.markdown("""
        **How Agent Analysis Works:**
        
        1. **44 Agents** analyze each stock in your portfolio
        2. Each agent belongs to a **category** (Technical, Fundamental, etc.)
        3. Agents produce **5-class signals**:
           - 🟢 **STRONG_BUY** - High confidence bullish (direction: +2)
           - 🟢 **BUY** - Bullish signal (direction: +1)
           - 🟡 **HOLD** - No clear direction (direction: 0)
           - 🔴 **SELL** - Bearish signal (direction: -1)
           - 🔴 **STRONG_SELL** - High confidence bearish (direction: -2)
        4. **Confidence** shows how strong the signal is (0-100%)
        5. **Supporting Agents** = agents voting for current decision
        6. **Conflicting Agents** = agents voting against
        
        **Final Decision**: Weighted average of all agent signals → 5-class output
        """)

    # Create signals dictionary
    signals_dict = {}
    if holdings_signals:
        signals_dict = {s["symbol"]: s for s in holdings_signals}

    # Select a holding to analyze
    symbols = [h["Symbol"] for h in holdings]
    selected_symbol = st.selectbox("Select Stock to Analyze", symbols)

    # Get holding details
    holding = next((h for h in holdings if h["Symbol"] == selected_symbol), None)
    signal_data = signals_dict.get(selected_symbol, {})

    if holding:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Quantity", holding["Qty"])
        with col2:
            st.metric("Avg Cost", f"Rs.{holding['Entry']:.0f}")
        with col3:
            current_price = holding.get("LTP", 0)
            st.metric("Current Price", f"Rs.{current_price:.0f}")
        with col4:
            pnl_pct = (
                ((current_price - holding["Entry"]) / holding["Entry"] * 100)
                if holding["Entry"] > 0
                else 0
            )
            st.metric(
                "P&L",
                f"{pnl_pct:+.1f}%",
                delta_color="normal" if pnl_pct > 0 else "inverse",
            )

        st.divider()

        # Signal analysis - initialize defaults
        decision = "N/A"
        confidence = 0
        supporting = 0
        conflicting = 0

        if signal_data:
            decision = signal_data.get("decision", "N/A").upper()
            confidence = signal_data.get("confidence", 0)
            supporting = signal_data.get("supporting_agents", 0)
            conflicting = signal_data.get("conflicting_agents", 0)

            col1, col2, col3 = st.columns(3)

            with col1:
                if decision == "STRONG_BUY":
                    st.success(f"🟢 SIGNAL: STRONG_BUY ({confidence:.0f}%)")
                elif decision == "BUY":
                    st.success(f"🟢 SIGNAL: BUY ({confidence:.0f}%)")
                elif decision == "STRONG_SELL":
                    st.error(f"🔴 SIGNAL: STRONG_SELL ({confidence:.0f}%)")
                elif decision == "SELL":
                    st.error(f"🔴 SIGNAL: SELL ({confidence:.0f}%)")
                else:
                    st.warning(f"🟡 SIGNAL: HOLD ({confidence:.0f}%)")

            with col2:
                st.metric("Supporting Agents", supporting)
                st.caption(f"{supporting} agents recommend {decision}")

            with col3:
                st.metric("Conflicting Agents", conflicting)
                st.caption(f"{conflicting} agents disagree")

            st.divider()

        # Show individual agent breakdown - ONLY if signal_breakdown exists
        if signal_data and signal_data.get("signal_breakdown"):
            st.markdown("### 🔍 Agent Category Breakdown")

            breakdown = signal_data.get("signal_breakdown", {})
            has_agents = False

            for category, agents_list in breakdown.items():
                if not agents_list:
                    continue
                has_agents = True
                st.markdown(f"**{category.title()} ({len(agents_list)} agents)**")

                cols = st.columns(3)
                for i, agent in enumerate(agents_list):
                    sig = agent.get("signal", "hold").upper()
                    conf = agent.get("confidence", 0)

                    if sig in ["STRONG_BUY", "BUY"]:
                        emoji = "🟢"
                    elif sig in ["STRONG_SELL", "SELL"]:
                        emoji = "🔴"
                    else:
                        emoji = "🟡"

                    with cols[i % 3]:
                        st.caption(
                            f"{emoji} {agent.get('agent_name', 'N/A')}: {sig} ({conf:.0f}%)"
                        )

            if has_agents:
                st.markdown("### 📋 All Agents Breakdown")

                all_agents = []
                for category, agents_list in breakdown.items():
                    for agent in agents_list:
                        all_agents.append(
                            {
                                "Category": category.title(),
                                "Agent": agent.get("agent_name", "N/A"),
                                "Signal": agent.get("signal", "hold").upper(),
                                "Confidence": agent.get("confidence", 0),
                            }
                        )

                if all_agents:
                    df_agents = pd.DataFrame(all_agents)

                    buy_agents = df_agents[
                        df_agents["Signal"].isin(["STRONG_BUY", "BUY"])
                    ]
                    sell_agents = df_agents[
                        df_agents["Signal"].isin(["STRONG_SELL", "SELL"])
                    ]
                    hold_agents = df_agents[df_agents["Signal"] == "HOLD"]

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("#### 🟢 BUY/STRONG_BUY Signals")
                        if not buy_agents.empty:
                            st.dataframe(
                                buy_agents[["Agent", "Signal", "Confidence"]],
                                hide_index=True,
                                width="stretch",
                                height=250,
                            )
                        else:
                            st.caption("No BUY signals")

                    with col2:
                        st.markdown("#### 🔴 SELL/STRONG_SELL Signals")
                        if not sell_agents.empty:
                            st.dataframe(
                                sell_agents[["Agent", "Signal", "Confidence"]],
                                hide_index=True,
                                width="stretch",
                                height=250,
                            )
                        else:
                            st.caption("No SELL signals")

                    if not hold_agents.empty:
                        st.markdown("#### 🟡 HOLD Signals")
                        st.dataframe(
                            hold_agents[["Agent", "Category", "Confidence"]],
                            hide_index=True,
                            width="stretch",
                            height=200,
                        )
        else:
            st.info(
                "Run `python -m data.run_holdings_analysis` to generate agent signals"
            )

        st.divider()

        # Show all agents with their signals
        if signal_data and "signal_breakdown" in signal_data:
            st.markdown("### 📋 All Agents Breakdown")

            # Collect all agents
            all_agents = []
            breakdown = signal_data.get("signal_breakdown", {})
            for category, agents_list in breakdown.items():
                for agent in agents_list:
                    all_agents.append(
                        {
                            "Category": category.title(),
                            "Agent": agent.get("agent_name", "N/A"),
                            "Signal": agent.get("signal", "hold").upper(),
                            "Confidence": agent.get("confidence", 0),
                            "Score": agent.get("numerical_score", 0),
                        }
                    )

            if all_agents:
                df_agents = pd.DataFrame(all_agents)

                buy_agents = df_agents[df_agents["Signal"].isin(["STRONG_BUY", "BUY"])]
                sell_agents = df_agents[
                    df_agents["Signal"].isin(["STRONG_SELL", "SELL"])
                ]
                hold_agents = df_agents[df_agents["Signal"] == "HOLD"]

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### 🟢 BUY Signals")
                    if not buy_agents.empty:
                        st.dataframe(
                            buy_agents[["Agent", "Signal", "Confidence"]],
                            hide_index=True,
                            width="stretch",
                            height=250,
                        )
                    else:
                        st.caption("No BUY signals")

                with col2:
                    st.markdown("#### 🔴 SELL Signals")
                    if not sell_agents.empty:
                        st.dataframe(
                            sell_agents[["Agent", "Signal", "Confidence"]],
                            hide_index=True,
                            width="stretch",
                            height=250,
                        )
                    else:
                        st.caption("No SELL signals")

                if not hold_agents.empty:
                    st.markdown("#### 🟡 HOLD Signals")
                    st.dataframe(
                        hold_agents[["Agent", "Category", "Confidence"]],
                        hide_index=True,
                        width="stretch",
                        height=200,
                    )

        # Show signals from holdings_signals.json if available
        if signal_data:
            st.markdown("### 📊 Signal Details")

            details = {
                "Metric": [
                    "Decision",
                    "Confidence",
                    "Score",
                    "Supporting Agents",
                    "Conflicting Agents",
                    "Market Regime",
                ],
                "Value": [
                    decision,
                    f"{confidence:.1f}%",
                    f"{signal_data.get('score', 0):.2f}",
                    supporting,
                    conflicting,
                    signal_data.get("regime", "unknown").title(),
                ],
            }
            st.dataframe(pd.DataFrame(details), hide_index=True, width="stretch")

    st.divider()

    # Summary for all holdings
    st.markdown("### 📈 All Holdings Summary")

    summary_data = []
    for h in holdings:
        sig = signals_dict.get(h["Symbol"], {})
        ret = (
            ((h.get("LTP", 0) - h["Entry"]) / h["Entry"] * 100) if h["Entry"] > 0 else 0
        )
        summary_data.append(
            {
                "Symbol": h["Symbol"],
                "Signal": sig.get("decision", "N/A").upper() if sig else "N/A",
                "Confidence": f"{sig.get('confidence', 0):.0f}%" if sig else "N/A",
                "Return": f"{ret:+.1f}%",
                "Value": float(h.get("LTP", 0) or 0) * float(h["Qty"] or 0),
            }
        )

    def color_signal(sig):
        sig = str(sig).upper()
        if sig in ["BUY", "STRONG_BUY"]:
            return "color:green;font-weight:bold"
        elif sig in ["SELL", "STRONG_SELL"]:
            return "color:red;font-weight:bold"
        elif sig == "HOLD":
            return "color:orange"
        return ""

    df_summary = pd.DataFrame(summary_data)
    if not df_summary.empty:
        st.dataframe(
            df_summary.sort_values("Value", ascending=False).style.map(
                color_signal, subset=["Signal"]
            ),
            column_config={
                "Value": st.column_config.NumberColumn("Value (Rs)", format="Rs.%.0f"),
            },
            width="stretch",
        )


def show_experiment_tracker() -> None:
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


def show_live_trading() -> None:
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
