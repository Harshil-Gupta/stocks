# stocks

A comprehensive quantitative trading system with multi-agent architecture for stock analysis and trading signal generation.

## Project Overview

This repository contains a production-grade quantitative trading system that leverages specialized AI agents to analyze markets and generate trading signals. The system supports both US (NYSE, NASDAQ) and Indian (NSE, BSE) markets.

## Features

### Multi-Agent Trading System (40+ Agents)

- **Technical Analysis**: RSI, MACD, Momentum, Trend, Breakout, Volume, Bollinger Bands, ATR, Support/Resistance, Volume Profile, Ichimoku Cloud, Williams %R, CCI, ADX, OBV, VWAP, MFI, Keltner Channels, Donchian Channels

- **Fundamental Analysis**: Valuation, Earnings, Cashflow, Growth, Dividend, Balance Sheet, Industry Comparison, Management Quality

- **Sentiment Analysis**: News Sentiment, Analyst Ratings, Insider Trading, Social Sentiment

- **Risk Management**: Volatility Regime, Tail Risk, Drawdown, Correlation Risk

- **Macro Economics**: Interest Rate, Inflation, GDP, Sector Rotation, Currency, Commodity

- **Market Structure**: Options Flow, Dark Pool, Order Imbalance, Put/Call Ratio

- **Quantitative Strategies**: Mean Reversion, Statistical Arbitrage, Factor Model, Pairs Trading

- **India-Specific**: India VIX, F&O, Nifty Sentiment, MF Holdings

### System Capabilities

- Parallel agent execution with configurable workers
- Signal aggregation with regime-based weighting
- Backtesting engine with comprehensive metrics
- Portfolio management with risk controls
- Mutual Fund data engine
- Smart money tracking (MF/FII)
- RBI macro data integration
- Screener.in & NSE API integration

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Analyze a stock
cd quant-agent-trader
python main.py analyze --symbol AAPL

# Backtest
python main.py backtest --symbols AAPL,GOOGL --start 2023-01-01 --end 2024-01-01

# Live mode
python main.py live --symbols AAPL,MSFT
```

## Project Structure

```
├── quant-agent-trader/     # Main trading system
│   ├── agents/            # Trading agents
│   │   ├── technical/     # Technical analysis agents
│   │   ├── fundamental/   # Fundamental analysis agents
│   │   ├── sentiment/     # Sentiment agents
│   │   ├── risk/          # Risk management agents
│   │   ├── macro/         # Macro economic agents
│   │   ├── market_structure/  # Market structure agents
│   │   ├── quant/         # Quantitative strategy agents
│   │   └── india/         # India-specific agents
│   ├── config/            # Configuration
│   ├── data/              # Data ingestion
│   ├── signals/           # Signal processing
│   ├── orchestration/     # Agent orchestration
│   └── tests/             # Test suite
```

## Requirements

See `requirements.txt` for dependencies.
