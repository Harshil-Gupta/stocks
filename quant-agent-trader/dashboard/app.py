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
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


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
    st.set_page_config(
        page_title="Quant Agent Trader",
        page_icon="📈",
        layout="wide"
    )

    # The page will now auto refresh every 60 seconds.
    st_autorefresh(interval=600000, key="datarefresh")
    
    st.title("📈 Quant Agent Trader Dashboard")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview", "Signals", "Portfolio", "Backtest", "Agents"
    ])
    
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
    
    # Load portfolio data
    portfolio = load_json("portfolio.json")
    holdings_signals = load_json("holdings_signals.json")
    market_regime = load_json("market_regime.json")
    
    # Calculate metrics
    if portfolio:
        df_port = pd.DataFrame(portfolio)
        total_value = (df_port['LTP'] * df_port['Qty']).sum()
        total_invested = (df_port['Entry'] * df_port['Qty']).sum()
        total_pnl = total_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        active_positions = len(portfolio)
    else:
        total_value = 0
        total_pnl = 0
        total_pnl_pct = 0
        active_positions = 0
    
    # Calculate signal accuracy
    if holdings_signals:
        total_signals = len(holdings_signals)
        buy_signals = sum(1 for s in holdings_signals if s.get("decision", "").upper() == "BUY")
        sell_signals = sum(1 for s in holdings_signals if s.get("decision", "").upper() == "SELL")
        hold_signals = sum(1 for s in holdings_signals if s.get("decision", "").upper() == "HOLD")
        
        # Calculate average confidence
        avg_confidence = sum(s.get("confidence", 0) for s in holdings_signals) / total_signals if total_signals > 0 else 0
    else:
        total_signals = 0
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        avg_confidence = 0
    
    # Get regime
    regime = market_regime.get("regime", "Unknown") if market_regime else "Unknown"
    regime_emoji = {"bull": "↗", "bear": "↘", "normal": "→", "volatile": "↕"}.get(regime.lower(), "→")
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Positions", str(active_positions))
    
    with col2:
        pnl_emoji = "+" if total_pnl >= 0 else ""
        st.metric("Total P&L", f"Rs.{total_pnl:,.0f}", f"{pnl_emoji}{total_pnl_pct:.1f}%")
    
    with col3:
        st.metric("Avg Signal Confidence", f"{avg_confidence:.1f}%")
    
    with col4:
        st.metric("Market Regime", regime.title(), regime_emoji)
    
    st.divider()
    
    # Holdings with signals table
    if portfolio and holdings_signals:
        st.subheader("Holdings with Signals")
        
        # Merge portfolio with signals
        signals_dict = {s["symbol"]: s for s in holdings_signals}
        
        holdings_data = []
        for pos in portfolio:
            symbol = pos["Symbol"]
            signal = signals_dict.get(symbol, {})
            
            # Calculate today's P&L for this position
            position_pnl = (pos["LTP"] - pos["Entry"]) * pos["Qty"]
            position_pnl_pct = ((pos["LTP"] - pos["Entry"]) / pos["Entry"] * 100) if pos["Entry"] > 0 else 0
            
            holdings_data.append({
                "Symbol": symbol,
                "Qty": pos["Qty"],
                "Entry": pos["Entry"],
                "LTP": pos["LTP"],
                "P&L": position_pnl,
                "P&L%": position_pnl_pct,
                "Signal": signal.get("decision", "N/A"),
                "Confidence": signal.get("confidence", 0),
                "Score": signal.get("score", 0)
            })
        
        df_holdings = pd.DataFrame(holdings_data)
        
        # Color function for signals
        def color_signal_val(val):
            val_upper = str(val).upper()
            if val_upper == "BUY":
                return "color:green;font-weight:bold"
            if val_upper == "SELL":
                return "color:red;font-weight:bold"
            if val_upper == "HOLD":
                return "color:orange"
            return ""
        
        def color_pnl_val(val):
            if val > 0:
                return "color:green"
            if val < 0:
                return "color:red"
            return ""
        
        st.dataframe(
            df_holdings.style.map(color_signal_val, subset=["Signal"])
                            .map(color_pnl_val, subset=["P&L"]),
            column_config={
                "Signal": st.column_config.TextColumn("Signal"),
                "Confidence": st.column_config.ProgressColumn("Confidence", format="%.0f%%", min_value=0, max_value=100),
                "P&L": st.column_config.NumberColumn("P&L", format="Rs.%.0f"),
                "P&L%": st.column_config.NumberColumn("P&L%", format="%.1f%%"),
                "Score": st.column_config.NumberColumn("Score", format="%.2f"),
            },
            use_container_width=True
        )
        
        # Signal distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Signal Distribution")
            signal_dist = {"BUY": buy_signals, "HOLD": hold_signals, "SELL": sell_signals}
            st.bar_chart(pd.Series(signal_dist))
        
        with col2:
            st.subheader("Portfolio Allocation")
            df_holdings['Value'] = df_holdings['LTP'] * df_holdings['Qty']
            top_holdings = df_holdings.nlargest(10, 'Value')[['Symbol', 'Value']]
            top_holdings = top_holdings.set_index('Symbol')['Value']
            st.bar_chart(top_holdings)
    
    elif portfolio:
        st.subheader("Holdings (no signals)")
        df_port = pd.DataFrame(portfolio)
        st.dataframe(df_port, use_container_width=True)
        st.info("Run analysis to generate signals: python -m data.run_holdings_analysis")
    
    else:
        st.warning("No holdings data. Import your holdings first.")
    
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
        regime = st.selectbox("Market Regime", ["Bull", "Bear", "Sideways", "High Volatility"])
    
    with col2:
        st.write("Current regime weights:")
        
        weights = {
            "Technical": 0.30,
            "Fundamental": 0.25,
            "Sentiment": 0.15,
            "Macro": 0.10,
            "Risk": 0.10,
            "Market Structure": 0.10
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
            "Confidence": st.column_config.ProgressColumn("Confidence", format="%d%%", min_value=0, max_value=100),
            "Score": st.column_config.NumberColumn("Score",format="%.2f"),
        },
        width="stretch"
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
    
    positions = load_json("portfolio.json")

    if positions is None:
        st.info("📥 No portfolio data loaded")
        st.markdown("""
        **To import your holdings:**
        1. Export holdings from your broker (Zerodha/Upstox) as CSV
        2. Run: `python -m data.import_portfolio <path_to_csv>`
        
        Expected CSV columns: Instrument, Qty., Avg. cost, LTP, P&L, Net chg.
        """)
        return
    
    df_port = pd.DataFrame(positions)
    def color_pnl(val):
        if "-" in str(val):
            return "color:red"
        return "color:green"

    st.dataframe(
        df_port.style.map(color_pnl, subset=["P&L"]),
        use_container_width=True
    )
    
    # Calculate allocation from real data
    total_value = (df_port['LTP'] * df_port['Qty']).sum()
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Allocation")
        
        # Calculate allocation from actual holdings
        df_port['Value'] = df_port['LTP'] * df_port['Qty']
        df_port['Weight'] = (df_port['Value'] / total_value * 100).round(1)
        allocation = dict(zip(df_port['Symbol'], df_port['Weight']))
        
        if len(allocation) > 0:
            st.bar_chart(pd.Series(allocation))
        else:
            st.warning("No positions to display")
    
    with col2:
        st.subheader("Risk Metrics")
        
        # Calculate metrics from real data
        total_invested = (df_port['Entry'] * df_port['Qty']).sum()
        total_pnl_val = total_value - total_invested
        total_pnl_pct = (total_pnl_val / total_invested * 100) if total_invested > 0 else 0
        
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
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    returns = [2.5, 1.8, -1.2, 3.4, 2.1, -0.8, 4.2, 1.5, -2.1, 3.8, 2.2, 1.1]
    
    chart_data = pd.DataFrame({
        "Month": months,
        "Return": returns
    })
    
    st.bar_chart(chart_data.set_index("Month"))
    
    st.divider()
    
    st.subheader("Drawdown Chart")
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=90), periods=90)
    drawdown = -np.cumsum(np.maximum(0, -np.random.randn(90) * 0.5))
    
    dd_data = pd.DataFrame({
        "date": dates,
        "drawdown": drawdown
    })
    
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
            "Avg Accuracy": st.column_config.ProgressColumn("Accuracy", format="%.0f%%", min_value=0, max_value=1),
        },
        width="stretch"
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
        {"ID": "exp_001", "Strategy": "Momentum", "Sharpe": 1.82, "Drawdown": "-12%", "Status": "Completed"},
        {"ID": "exp_002", "Strategy": "Mean Reversion", "Sharpe": 1.45, "Drawdown": "-8%", "Status": "Completed"},
        {"ID": "exp_003", "Strategy": "ML Meta", "Sharpe": 2.15, "Drawdown": "-10%", "Status": "Running"},
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
            last_trade = trades[0].get('Time', 'N/A')
            st.write(f"Last trade: {last_trade}")
    
    st.divider()
    
    st.subheader("Recent Trades")
    
    st.table(pd.DataFrame(trades))


if __name__ == "__main__":
    main()
