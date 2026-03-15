# Quant Agent Trader

A production-grade multi-agent quantitative trading system with parallel agent execution, signal aggregation, ML meta-models, and portfolio management. Supports both US and Indian markets (NSE/BSE).

> **Note**: This is now a complete Quant Research Platform with 40+ agents, walk-forward validation, ML meta-models, and institutional-grade features.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run analysis
python main.py analyze --symbol RELIANCE

# Run research with walk-forward validation
python main.py research --symbol TCS --start 2020 --end 2024 --walk-forward

# Launch dashboard
streamlit run dashboard/app.py
```

## What's New (v3.0)

- **5-Class Signal Classification**: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL for more context
- **Upstox API V3 Integration**: Real historical data from Indian markets
- **Vectorized Backtesting**: 100x faster event-driven backtesting
- **Feature Engineering Pipeline**: 19 modular technical indicators
- **Portfolio Optimization**: Mean-Variance, Max Sharpe, Risk Parity, Black-Litterman
- **Strategy Plugin System**: Extensible strategy architecture
- **Research Platform**: Experiment tracking, hyperparameter optimization
- **Production Deployment**: Docker, Makefile, structured logging

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     QUANT RESEARCH PLATFORM                      │
├─────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                    │
│    ├── data/ingestion/upstox_v3.py  # Upstox API V3            │
│    ├── data/cache/                 # Parquet caching            │
│    └── data/validators.py          # Quality checks             │
├─────────────────────────────────────────────────────────────────┤
│  FEATURE ENGINEERING                                           │
│    ├── features/generators/         # 19 technical indicators    │
│    ├── features/pipeline.py        # No-lookahead-bias design   │
│    └── features/config.py          # Strategy presets            │
├─────────────────────────────────────────────────────────────────┤
│  AGENT LAYER                                                   │
│    ├── agents/technical/ (18)       # Technical agents           │
│    ├── agents/fundamental/ (8)      # Fundamental agents        │
│    ├── agents/sentiment/ (4)        # Sentiment agents           │
│    └── signals/                     # Schema + aggregator        │
├─────────────────────────────────────────────────────────────────┤
│  STRATEGY LAYER                                                │
│    ├── strategies/__init__.py       # Plugin system (5-class)    │
│    └── strategies/plugin_system.py  # Strategy ensembles         │
├─────────────────────────────────────────────────────────────────┤
│  BACKTESTING                                                   │
│    ├── backtesting/vectorized.py    # Vectorized engine          │
│    └── backtesting/engine.py        # Event-driven engine        │
├─────────────────────────────────────────────────────────────────┤
│  PORTFOLIO                                                     │
│    ├── portfolio/optimizer.py       # Mean-Variance, Black-Litterman│
│    └── risk/risk_engine.py         # Risk controls             │
├─────────────────────────────────────────────────────────────────┤
│  RESEARCH                                                      │
│    ├── research/                   # Experiment tracker         │
│    └── analytics/                  # Performance metrics        │
├─────────────────────────────────────────────────────────────────┤
│  EXECUTION                                                     │
│    └── quant_system.py             # Main orchestrator          │
└─────────────────────────────────────────────────────────────────┘
```

## 5-Class Signal System

The system now supports 5-level signal classification for more nuanced trading decisions:

| Signal | Direction | Position |
|--------|-----------|----------|
| STRONG_BUY | +2 | Full long (100%) |
| BUY | +1 | Half long (50%) |
| HOLD | 0 | No position |
| SELL | -1 | Half short (50%) |
| STRONG_SELL | -2 | Full short (100%) |

### Signal Flow

```
Strategy/Agent → SignalType (5-class) → Direction (-2 to +2) → Backtest Engine
```

```python
from signals.signal_schema import AgentSignal, SignalType

# Agents generate 5-class signals
signal = AgentSignal(
    agent_name="rsi_agent",
    agent_category="technical",
    signal="strong_buy",  # 5-class: strong_buy, buy, hold, sell, strong_sell
    confidence=85.0,
    numerical_score=-0.8
)

# Get numeric direction for backtesting
direction = signal.direction  # Returns: 2 (for strong_buy)
is_buy = signal.is_buy       # True for strong_buy, buy
is_strong = signal.is_strong # True for strong_buy, strong_sell
```

## Usage Examples

### Analysis with Upstox Data

```bash
# Analyze single stock using Upstox API
python main.py analyze --symbol RELIANCE

# Analyze multiple stocks
python main.py analyze --symbol TCS,HDFCBANK,INFY
```

### Backtesting with 5-Class Signals

```python
from quant_system import QuantSystem

system = QuantSystem()

# Run backtest with vectorized engine
result = system.backtest(
    symbols=["RELIANCE", "TCS"],
    start_date="2023-01-01",
    end_date="2024-01-01",
    strategy="ma_crossover",
    strategy_params={"short_window": 20, "long_window": 50}
)

print(f"Return: {result.metrics['total_return']:.2%}")
print(f"Sharpe: {result.metrics['sharpe_ratio']:.2f}")
```

### Research with Experiment Tracking

```python
from research import ExperimentTracker, HyperparameterOptimizer

tracker = ExperimentTracker("research/results")
tracker.log_strategy("MA Crossover", params, metrics)

# Grid search for optimal parameters
optimizer = HyperparameterOptimizer(
    strategy_func=run_strategy,
    parameter_grid={"short_window": [10, 20, 30], "long_window": [50, 100]}
)
result = optimizer.optimize(symbols=["RELIANCE"], start_date="2023", end_date="2024")
```

## Feature Engineering Pipeline

```python
from features import FeaturePipeline, FeatureConfig, FeatureMode

config = FeatureConfig(min_history=200)
config.set_strategy("momentum")  # Preset: momentum, mean_reversion, breakout

pipeline = FeaturePipeline(config)
features = pipeline.compute_features(data, mode=FeatureMode.INFERENCE)

# 19 built-in features:
# SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX, 
# Stochastic, Williams %R, CCI, OBV, VWAP, etc.
```

## Portfolio Optimization

```python
from portfolio.optimization import PortfolioOptimizer, OptimizationMethod

optimizer = PortfolioOptimizer(method=OptimizationMethod.MAX_SHARPE)
result = optimizer.optimize(expected_returns, covariance_matrix)

# Multiple methods available:
# - MEAN_VARIANCE: Classic Markowitz
# - MAX_SHARPE: Maximum Sharpe ratio
# - MIN_VARIANCE: Minimum volatility
# - RISK_PARITY: Equal risk contribution
# - BLACK_LITTERMAN: Bayesian views
```

## Strategy Plugins

```python
from strategies import create_strategy, StrategyEnsemble, SignalType

# Create individual strategies
ma_strategy = create_strategy("ma_crossover", short_window=20, long_window=50)
rsi_strategy = create_strategy("rsi", period=14)

# Ensemble with voting
ensemble = StrategyEnsemble([ma_strategy, rsi_strategy], method="voting")
signal = ensemble.generate_signals(data)

# 5-class output
print(signal.signal)  # strong_buy, buy, hold, sell, strong_sell
```

## Supported Markets

### Indian Markets (Primary)
- **Data Source**: Upstox API V3 (with yfinance fallback)
- **Exchanges**: NSE, BSE
- **Instruments**: EQ, EQ Derivatives, Currency

### US Markets (Fallback)
- **Data Source**: yfinance
- **Stocks**: AAPL, GOOGL, MSFT, TSLA, etc.
- **ETFs**: SPY, QQQ, DIA, IWM

## Agent Categories (50+ Agents)

| Category | Count | Examples |
|----------|-------|----------|
| Technical | 18 | RSI, MACD, Momentum, Bollinger, VWAP |
| Fundamental | 8 | Valuation, Earnings, CRISIL |
| Sentiment | 4 | News, Social, Analyst Ratings |
| Macro | 6 | Interest Rate, Inflation, GDP |
| Risk | 5 | Drawdown, Correlation, Tail Risk |
| Market Structure | 8 | Options Flow, Order Imbalance |

## Project Structure

```
quant-agent-trader/
├── agents/                    # Trading agents (50+)
│   ├── technical/            # RSI, MACD, Momentum, etc.
│   ├── fundamental/          # Valuation, Earnings
│   ├── sentiment/            # News, Social
│   └── base_agent.py         # Base class with caching
├── signals/                  # Signal processing
│   ├── signal_schema.py      # 5-class signal structures
│   ├── signal_aggregator.py  # Weighted ensemble aggregation
│   └── feature_extractor.py  # ML features
├── features/                 # Feature engineering
│   ├── generators/          # 19 technical indicators
│   ├── pipeline.py          # No-lookahead-bias pipeline
│   └── config.py            # Strategy presets
├── backtesting/              # Backtesting engines
│   ├── vectorized.py        # Vectorized (100x faster)
│   └── engine.py            # Event-driven
├── portfolio/                # Portfolio management
│   └── optimization.py      # Mean-Variance, Risk Parity
├── risk/                     # Risk management
│   └── risk_engine.py       # Position limits, drawdown
├── research/                 # Research platform
│   ├── experiment_tracker.py # SQLite tracking
│   └── hyperparameter_opt.py # Grid/Random search
├── data/                     # Data layer
│   ├── ingestion/upstox_v3.py # Upstox API client
│   └── cache/               # Parquet caching
├── analytics/                # Performance metrics
│   └── performance_metrics.py # 20+ metrics
├── strategies/               # Strategy plugins
│   ├── __init__.py          # 5-class strategies
│   └── plugin_system.py      # Ensemble voting
├── utils/                    # Utilities
│   ├── logging_config.py    # Structured logging
│   └── monitoring.py        # Alerts
├── quant_system.py           # Main orchestrator
├── Makefile                  # Production commands
├── Dockerfile                # Container deployment
└── main.py                   # CLI entry point
```

## Installation

```bash
# Clone and setup
git clone https://github.com/your-repo/quant-agent-trader.git
cd quant-agent-trader

# Create venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Setup Upstox (optional)
# Add UPSTOX_API_KEY to .env file

# Run
python main.py analyze --symbol RELIANCE

# Or launch dashboard
streamlit run dashboard/app.py
```

## Production Deployment

```bash
# Using Makefile
make setup          # Install dependencies
make run            # Run main.py
make backtest       # Run backtest
make dashboard      # Launch Streamlit

# Using Docker
make docker-up      # Start containerized environment
```

## Configuration

### 5-Class Signal Weights by Regime

```python
# Signals are aggregated with category weights adjusted by regime
REGIME_WEIGHTS = {
    "bull": {"technical": 0.30, "fundamental": 0.25, "sentiment": 0.15, ...},
    "bear": {"technical": 0.15, "fundamental": 0.25, "sentiment": 0.10, ...},
    "sideways": {"technical": 0.25, "fundamental": 0.20, "sentiment": 0.15, ...},
    "high_volatility": {"technical": 0.15, "fundamental": 0.20, "sentiment": 0.10, ...}
}

# Aggregation converts to 5-class:
# final_score >= 0.6 → strong_buy
# final_score >= 0.2 → buy  
# -0.2 < final_score < 0.2 → hold
# final_score <= -0.2 → sell
# final_score <= -0.6 → strong_sell
```

### Environment Variables

```bash
# Upstox API (for Indian markets)
UPSTOX_API_KEY=your_api_key

# Data paths
DATA_DIR=data
CACHE_DIR=data/cache
RESULTS_DIR=research/results

# Trading
INITIAL_CAPITAL=100000
RISK_FREE_RATE=0.06
```

## Holdings Configuration

The system requires your portfolio holdings to function.

### 1. Create Holdings Directory

```bash
# Default: C:\Users\Harshil\Desktop\holdings (Windows)
# Or configure custom path in .env
```

### 2. Export Holdings from Broker

Export your holdings CSV from your broker (Zerodha/Upstox) and save to the holdings directory.

**Expected CSV format:**
```
Instrument,Qty.,Avg. cost,LTP,Invested,Cur. val,P&L,Net chg.,Day chg.
RELIANCE,100,1350.00,1424.00,135000,142400,7400,5.48,-1.2
```

## Troubleshooting

- **Import errors**: Install all dependencies `pip install -r requirements.txt`
- **No data**: Check internet connection or Upstox API keys
- **Agent errors**: Some agents fail gracefully if features are missing
- **Streamlit issues**: Ensure streamlit is installed `pip install streamlit`

## License

MIT
