# Quant Agent Trader

A production-grade multi-agent quantitative trading system with parallel agent execution, signal aggregation, and portfolio management. Supports both US and Indian markets (NSE/BSE).

## Project Overview

The Quant Agent Trader is a sophisticated trading system that leverages multiple specialized agents to analyze stocks and generate trading signals. Each agent focuses on different aspects of market analysis, and signals are aggregated using a weighted scoring system that adapts to market regimes.

### Key Features

- **Multi-Agent Architecture**: Parallel execution of multiple trading agents
- **Market Support**: US markets (NYSE, NASDAQ) and Indian markets (NSE, BSE)
- **Signal Aggregation**: Intelligent combination of agent signals with regime-based weighting
- **Backtesting Engine**: Comprehensive historical simulation with detailed metrics
- **Portfolio Management**: Position sizing, risk management, and rebalancing
- **Technical Analysis**: RSI, MACD, Momentum, Trend, Breakout, Volume agents
- **India-Specific Agents**: India VIX, FNO, Nifty Sentiment, MF Holdings agents
- **Reinforcement Learning**: Feedback system for continuous strategy improvement

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Setup

1. Clone the repository and navigate to the project directory:

```bash
cd quant-agent-trader
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
```

3. Activate the virtual environment:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

### Optional API Keys

For enhanced data coverage, set environment variables:

```bash
# For US market data (optional)
export POLYGON_API_KEY="your_polygon_api_key"
export ALPHA_VANTAGE_KEY="your_alpha_vantage_key"

# Windows
set POLYGON_API_KEY=your_polygon_api_key
set ALPHA_VANTAGE_KEY=your_alpha_vantage_key
```

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    QuantTradingSystem                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Data Engine  │  │  Agents      │  │ Signal Aggregator│ │
│  │              │  │              │  │                  │ │
│  │ - US Data    │  │ - Technical  │  │ - Weighted scores│ │
│  │ - India Data │  │ - Sentiment  │  │ - Regime-based   │ │
│  │ - MF Data    │  │ - Fundamental│  │ - Confidence     │ │
│  └──────────────┘  │ - Risk       │  └──────────────────┘ │
│                    │ - India      │                        │
│                    └──────────────┘                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │ Backtest Engine  │  │ Agent Dispatcher               │  │
│  │                  │  │                                │  │
│  │ - Historical sim │  │ - Parallel execution           │  │
│  │ - Metrics        │  │ - Caching                      │  │
│  │ - Equity curves  │  │ - Retry logic                  │  │
│  └──────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Agent Categories

| Category | Description | Agents |
|----------|-------------|--------|
| **Technical** | Price/volume analysis | RSI, MACD, Momentum, Trend, Breakout, Volume |
| **Sentiment** | Market mood analysis | News Sentiment, Analyst Ratings |
| **Fundamental** | Financial metrics | Valuation, Earnings, Cashflow, Growth |
| **Risk** | Risk assessment | Volatility Regime, Tail Risk |
| **India** | India-specific | India VIX, FNO, Nifty Sentiment, MF Holdings |

### Signal Flow

1. Market data is fetched for the target symbol
2. Technical features are calculated (RSI, MACD, etc.)
3. All agents analyze the features and generate signals
4. Signals are aggregated based on market regime
5. Final trading decision is made (BUY/SELL/HOLD)

## Usage Examples

### Analyzing US Stocks

```bash
# Analyze a single US stock
python main.py analyze --symbol AAPL

# Analyze multiple US stocks
python main.py analyze --symbol AAPL,GOOGL,MSFT

# Analyze with custom data range
python main.py analyze --symbol TSLA --days 180
```

### Analyzing Indian Stocks

```bash
# Analyze a single NSE stock
python main.py analyze --symbol RELIANCE

# Analyze multiple NSE stocks
python main.py analyze --symbol TCS,HDFCBANK,INFY

# Analyze Nifty 50 index
python main.py analyze --symbol "NIFTY 50"

# Analyze with FNO and MF data
python main.py analyze --symbol RELIANCE,TCS
```

### Running Backtests

```bash
# Backtest US stocks
python main.py backtest --symbols AAPL,GOOGL --start 2023-01-01 --end 2024-01-01

# Backtest Indian stocks
python main.py backtest --symbols RELIANCE,TCS --start 2023-01-01 --end 2024-01-01

# Backtest with custom capital
python main.py backtest --symbols AAPL,MSFT,GOOGL --start 2022-01-01 --end 2024-01-01 --capital 500000
```

### Live Trading Mode

```bash
# Run in live analysis mode (placeholder)
python main.py live --symbols AAPL,MSFT

# Run with custom interval
python main.py live --symbols RELIANCE,INFY --interval 30
```

## Command Reference

### analyze

Analyze stock(s) and generate trading signals.

```bash
python main.py analyze --symbol SYMBOLS [--days DAYS]
```

| Argument | Description | Default |
|----------|-------------|---------|
| `--symbol`, `-s` | Stock symbol(s), comma-separated | Required |
| `--days` | Number of historical days | 365 |

### backtest

Run historical backtest on symbols.

```bash
python main.py backtest --symbols SYMBOLS --start DATE --end DATE [--capital CAPITAL]
```

| Argument | Description | Default |
|----------|-------------|---------|
| `--symbols` | Stock symbols, comma-separated | Required |
| `--start` | Start date (YYYY-MM-DD) | Required |
| `--end` | End date (YYYY-MM-DD) | Required |
| `--capital` | Initial capital | 100000 |

### live

Run in live trading analysis mode.

```bash
python main.py live --symbols SYMBOLS [--interval SECONDS]
```

| Argument | Description | Default |
|----------|-------------|---------|
| `--symbols` | Stock symbols, comma-separated | Required |
| `--interval` | Update interval in seconds | 60 |

## Supported Symbols

### US Markets

- US stocks: AAPL, GOOGL, MSFT, TSLA, AMZN, etc.
- Indices: SPY, QQQ, DIA, IWM

### Indian Markets (NSE)

| Symbol | Company |
|--------|---------|
| RELIANCE | Reliance Industries |
| TCS | Tata Consultancy Services |
| HDFCBANK | HDFC Bank |
| INFY | Infosys |
| HINDUNILVR | Hindustan Unilever |
| ICICIBANK | ICICI Bank |
| SBIN | State Bank of India |
| BHARTIARTL | Bharti Airtel |
| KOTAKBANK | Kotak Mahindra Bank |
| LT | Larsen & Toubro |
| BAJFINANCE | Bajaj Finance |
| M&M | Mahindra & Mahindra |

### Indian Indices

- NIFTY 50
- NIFTY Bank
- NIFTY IT
- NIFTY Pharma
- NIFTY Auto
- NIFTY Metal
- NIFTY FMCG
- INDIA VIX

## Configuration

The system can be configured via `config/settings.py`. Key configuration options:

### Agent Configuration

```python
@dataclass
class AgentConfig:
    max_concurrent_agents: int = 100      # Parallel agent execution
    agent_timeout: int = 30               # Timeout in seconds
    enable_caching: bool = True           # Enable signal caching
    cache_ttl: int = 3600                 # Cache TTL in seconds
    max_retries: int = 2                  # Retry failed agents
```

### Signal Weights by Regime

The system uses regime-based signal weighting:

```python
INDIA_REGIME_WEIGHTS = {
    "bull": {
        "technical": 0.30,
        "fundamental": 0.25,
        "sentiment": 0.15,
        "fno": 0.10,
        "india_vix": 0.10,
        "risk": 0.10
    },
    "bear": {
        "technical": 0.15,
        "fundamental": 0.25,
        "sentiment": 0.10,
        "fno": 0.10,
        "india_vix": 0.20,
        "risk": 0.20
    },
    "sideways": {
        "technical": 0.25,
        "fundamental": 0.20,
        "sentiment": 0.15,
        "fno": 0.10,
        "india_vix": 0.10,
        "risk": 0.20
    },
    "high_volatility": {
        "technical": 0.15,
        "fundamental": 0.20,
        "sentiment": 0.10,
        "fno": 0.15,
        "india_vix": 0.25,
        "risk": 0.15
    }
}
```

### Portfolio Configuration

```python
@dataclass
class PortfolioConfig:
    max_position_size: float = 0.10       # 10% max per position
    default_position_size: float = 0.05  # 5% default
    max_portfolio_stocks: int = 20       # Max holdings
    rebalance_threshold: float = 0.15    # Rebalance threshold
    risk_per_trade: float = 0.02         # 2% risk per trade
```

## Backtesting

The backtesting engine provides comprehensive performance metrics:

### Metrics Calculated

- **Performance**: Total Return, Annualized Return, Sharpe Ratio, Sortino Ratio, Calmar Ratio
- **Risk**: Max Drawdown, Volatility
- **Trading**: Win Rate, Profit Factor, Average Trade Return, Holding Period
- **Costs**: Total Commission, Total Slippage

### Example Output

```
============================================================
BACKTEST RESULTS
============================================================

Symbols: AAPL, GOOGL
Period: 2023-01-01 to 2024-01-01
Initial Capital: ₹100,000.00
Total Trades: 45

----------------------------------------
PERFORMANCE SUMMARY
----------------------------------------
  Total Return: 23.45%
  Annualized Return: 22.89%
  Annualized Volatility: 18.32%
  Sharpe Ratio: 1.25
  Sortino Ratio: 1.68
  Calmar Ratio: 2.15

----------------------------------------
RISK METRICS
----------------------------------------
  Max Drawdown: 12.34%
  Max Drawdown Value: ₹12,340.00

----------------------------------------
TRADE STATISTICS
----------------------------------------
  Total Trades: 45
  Winning Trades: 28
  Losing Trades: 17
  Win Rate: 62.22%
  Profit Factor: 1.85
  Avg Trade Return: 1.92%
  Avg Holding Period: 8.5 days
```

## Development

### Adding Custom Agents

1. Inherit from `BaseAgent`:

```python
from agents.base_agent import BaseAgent, AgentMetadata
from signals.signal_schema import AgentSignal, AgentCategory

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name="my_custom_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=AgentMetadata(
                version="1.0.0",
                description="My custom trading agent",
                required_features=["price", "volume", "rsi"]
            )
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        # Implement signal logic
        return AgentSignal(...)
```

2. Register the agent in `main.py`:

```python
from agents.technical.my_custom_agent import MyCustomAgent

# Add to agent list
self.agents.append(MyCustomAgent(config=agent_base_config))
```

### Project Structure

```
quant-agent-trader/
├── agents/
│   ├── base_agent.py          # Base agent class
│   ├── agent_dispatcher.py    # Agent execution dispatcher
│   ├── regime_classifier.py  # Market regime classification
│   ├── technical/             # Technical analysis agents
│   ├── sentiment/             # Sentiment analysis agents
│   ├── fundamental/          # Fundamental analysis agents
│   ├── risk/                 # Risk management agents
│   └── india/                # India-specific agents
├── config/
│   └── settings.py            # Configuration settings
├── data/
│   └── ingestion/            # Data ingestion modules
├── signals/
│   ├── signal_schema.py       # Signal data structures
│   └── signal_aggregator.py  # Signal aggregation logic
├── orchestration/
│   └── dispatcher.py          # Agent orchestration
├── backtesting/
│   └── engine.py             # Backtesting engine
├── portfolio/
│   └── portfolio_engine.py   # Portfolio management
├── features/
│   └── indicators.py         # Technical indicators
└── main.py                   # Main entry point
```

## Troubleshooting

### Common Issues

1. **No data fetched**: Check internet connection or set API keys
2. **Agent errors**: Some agents may fail if required features are missing
3. **Import errors**: Ensure all dependencies are installed
4. **Memory issues**: Reduce `max_concurrent_agents` in config

### Logging

Logs are written to `quant_trader.log`:

```bash
# View logs
tail -f quant_trader.log
```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
python main.py analyze --symbol AAPL
```

## License

MIT License

## Support

For issues and feature requests, please open an issue on the project repository.
