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

## What's New (v2.0)

- **ML Meta Model**: Agents → Features → ML Model → Decision
- **Walk-Forward Backtesting**: Professional train/test validation
- **Feature Store**: Persisted agent outputs in Parquet
- **Portfolio Optimizer**: Kelly Criterion, Risk Parity, Volatility Scaling
- **Signal Explainability**: Human-readable reasoning for decisions
- **Self-Evaluation Loop**: Agents learn from their mistakes
- **Market Microstructure**: Order book, VWAP, depth signals
- **Strategy Sandbox**: YAML-based strategy configs
- **Live Dashboard**: Streamlit visualization
- **Paper Trading**: Simulated execution with slippage

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     QUANT RESEARCH PLATFORM                      │
├─────────────────────────────────────────────────────────────────┤
│  DATA LAYER                                                    │
│    ├── data/feature_store.py      # Parquet persistence        │
│    ├── data/validators.py        # Quality checks              │
│    └── data/training_data_generator.py                          │
├─────────────────────────────────────────────────────────────────┤
│  AGENT LAYER                                                   │
│    ├── agents/technical/ (18)     # Technical agents           │
│    ├── agents/fundamental/ (8)    # Fundamental agents        │
│    ├── agents/market_microstructure.py # Order book, VWAP       │
│    └── signals/                   # Schema + aggregator        │
├─────────────────────────────────────────────────────────────────┤
│  ML LAYER                                                      │
│    ├── models/meta_model.py       # Training + inference        │
│    ├── models/scheduler.py       # Auto-retraining             │
│    └── models/registry.json      # Version management         │
├─────────────────────────────────────────────────────────────────┤
│  RESEARCH                                                      │
│    ├── research_engine.py       # Research CLI                │
│    ├── backtesting/walk_forward.py # Walk-forward validation    │
│    └── utils/experiment_tracker.py # Experiment logging        │
├─────────────────────────────────────────────────────────────────┤
│  PORTFOLIO                                                     │
│    ├── portfolio/optimizer.py    # Position sizing             │
│    └── risk/risk_engine.py      # Risk management            │
├─────────────────────────────────────────────────────────────────┤
│  EXECUTION                                                     │
│    ├── execution/paper_trader.py # Paper trading               │
│    └── utils/monitoring.py      # Alerts + Slack/Telegram   │
├─────────────────────────────────────────────────────────────────┤
│  DASHBOARD                                                     │
│    └── dashboard/app.py          # Streamlit visualization    │
└─────────────────────────────────────────────────────────────────┘
```

## Usage Examples

### Research Mode (New!)

```bash
# Run full research with walk-forward validation
python main.py research --symbol TCS --start 2018 --end 2024 --walk-forward

# Run with regime analysis
python main.py research --symbols RELIANCE,TCS --start 2020 --end 2024 --regime-analysis
```

### Analysis

```bash
# Analyze single stock
python main.py analyze --symbol RELIANCE

# Analyze multiple stocks
python main.py analyze --symbol TCS,HDFCBANK,INFY
```

### Backtesting

```bash
# Basic backtest
python main.py backtest --symbols RELIANCE,TCS --start 2023-01-01 --end 2024-01-01
```

### Dashboard

```bash
# Launch interactive dashboard
streamlit run dashboard/app.py
```

## ML Meta Model

The system now supports ML-based signal aggregation:

```python
from signals.feature_extractor import TrainingDataBuilder
from models.meta_model import MetaModelTrainer, ModelRegistry

# Generate training data
builder = TrainingDataBuilder()
dataset = builder.generate(data, agents, start_date, end_date)

# Train model
trainer = MetaModelTrainer(model_type="lightgbm")
trainer.train(dataset, target="target_binary_5d")

# Register model
registry = ModelRegistry()
registry.register_model(trainer.model, trainer.metadata, trainer.feature_names)

# Use in live trading
from signals.meta_model_aggregator import MetaModelAggregator
meta = MetaModelAggregator()
result = meta.aggregate_signals(signals, regime="bull", stock_symbol="TCS")
```

## Portfolio Optimization

```python
from portfolio.optimizer import PortfolioOptimizer

# Multiple sizing methods
optimizer = PortfolioOptimizer(method="kelly")      # Kelly Criterion
optimizer = PortfolioOptimizer(method="volatility")  # Volatility scaling
optimizer = PortfolioOptimizer(method="risk_parity") # Risk parity

positions = optimizer.optimize(signals, portfolio_value=100000)
```

## Self-Evaluation Loop

Agents learn from their performance:

```python
from utils.self_evaluation import AgentEvaluator

evaluator = AgentEvaluator()

# Record trade outcomes
evaluator.record_trade(
    symbol="TCS",
    signals=agent_signals,
    decision="buy",
    entry_price=3500,
    exit_price=3600,
    pnl=10000,
    holding_period=5
)

# Get performance
performance = evaluator.get_agent_performance()

# Identify weak agents
weak = evaluator.get_weak_agents(threshold=0.45)
```

## Strategy Sandbox

```yaml
# strategies/momentum_strategy.yaml
name: momentum_strategy
agents:
  - rsi_agent
  - macd_agent
  - momentum_agent
weights:
  technical: 0.80
  sentiment: 0.10
```

```python
from agents.plugin_manager import StrategyConfigLoader

loader = StrategyConfigLoader()
strategy = loader.load_strategy("strategies/momentum_strategy.yaml")
```

## Risk Management

```python
from risk.risk_engine import RiskEngine

risk = RiskEngine(max_position_size=0.25, max_daily_loss=0.05)
result = risk.check_trade("TCS", "buy", 100, 3500, portfolio_value)
```

## Monitoring

```python
from utils.monitoring import Monitor, SlackHandler

monitor = Monitor()
monitor.add_handler(SlackHandler(webhook_url="..."))
monitor.alert("Trade executed", level="info")
monitor.check_drawdown(0.15)
```

## Supported Markets

### US Markets
- AAPL, GOOGL, MSFT, TSLA, AMZN, etc.
- SPY, QQQ, DIA, IWM

### Indian Markets (NSE)
- RELIANCE, TCS, HDFCBANK, INFY, etc.
- NIFTY 50, NIFTY Bank, NIFTY IT, etc.

## Agent Categories (50+ Agents)

| Category | Count | Examples |
|----------|-------|----------|
| Technical | 18 | RSI, MACD, Momentum, Bollinger, VWAP |
| Fundamental | 8 | Valuation, Earnings, CRISIL |
| Sentiment | 4 | News, Social, Insider |
| Macro | 6 | Interest Rate, Inflation, GDP |
| Risk | 5 | Drawdown, Correlation, Tail Risk |
| Market Structure | 8 | Options Flow, Order Imbalance |
| Quant | 4 | Mean Reversion, Stat Arb |
| India-Specific | 4 | India VIX, F&O, MF Holdings |
| Microstructure | 6 | Order Book, VWAP Deviation |

## Project Structure

```
quant-agent-trader/
├── agents/                    # Trading agents (50+)
│   ├── technical/           # RSI, MACD, Momentum, etc.
│   ├── fundamental/          # Valuation, Earnings
│   ├── sentiment/            # News, Social
│   ├── market_microstructure.py  # Order book, VWAP
│   └── plugin_manager.py     # Dynamic agent loading
├── signals/                  # Signal processing
│   ├── signal_schema.py      # Data structures
│   ├── signal_aggregator.py  # Aggregation + explainability
│   ├── feature_extractor.py  # ML features
│   └── meta_model_aggregator.py  # ML-based aggregation
├── data/                     # Data layer
│   ├── feature_store.py     # Parquet persistence
│   ├── validators.py         # Quality checks
│   └── training_data_generator.py
├── models/                   # ML training
│   ├── meta_model.py        # Training + inference
│   └── scheduler.py          # Auto-retraining
├── backtesting/              # Backtesting
│   ├── engine.py            # Main engine
│   └── walk_forward.py       # Walk-forward validation
├── portfolio/                # Portfolio management
│   └── optimizer.py          # Position sizing
├── risk/                     # Risk management
│   └── risk_engine.py       # Risk controls
├── execution/               # Order execution
│   └── paper_trader.py      # Paper trading
├── utils/                    # Utilities
│   ├── experiment_tracker.py # Experiment logging
│   ├── profiler.py          # Performance profiling
│   ├── monitoring.py        # Alerts
│   ├── structured_logging.py
│   └── self_evaluation.py  # Agent self-learning
├── dashboard/                # Visualization
│   └── app.py               # Streamlit dashboard
├── strategies/               # Strategy configs
│   ├── momentum_strategy.yaml
│   ├── mean_reversion_strategy.yaml
│   └── ml_meta_strategy.yaml
├── research_engine.py         # Research CLI
└── main.py                   # Entry point
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

# Run
python main.py analyze --symbol RELIANCE

# Or launch dashboard
streamlit run dashboard/app.py
```

## Configuration

### Signal Weights by Regime

```python
REGIME_WEIGHTS = {
    "bull": {"technical": 0.30, "fundamental": 0.25, "sentiment": 0.15, "macro": 0.10, "risk": 0.10, "market_structure": 0.10},
    "bear": {"technical": 0.15, "fundamental": 0.25, "sentiment": 0.10, "macro": 0.15, "risk": 0.20, "market_structure": 0.15},
    "sideways": {"technical": 0.25, "fundamental": 0.20, "sentiment": 0.15, "macro": 0.10, "risk": 0.15, "market_structure": 0.15},
    "high_volatility": {"technical": 0.15, "fundamental": 0.20, "sentiment": 0.10, "macro": 0.15, "risk": 0.25, "market_structure": 0.15}
}
```

## Troubleshooting

- **Import errors**: Install all dependencies `pip install -r requirements.txt`
- **No data**: Check internet connection or API keys
- **Agent errors**: Some agents fail gracefully if features are missing
- **Streamlit issues**: Ensure streamlit is installed `pip install streamlit`

## License

MIT
