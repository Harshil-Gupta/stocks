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
- **Fundamental Analysis**: CRISIL ratings, Valuation, Earnings, Cashflow, Growth agents
- **Mutual Fund Data Engine**: Modular MF data ingestion with AMFI, MFAPI, ValueResearch sources
- **Smart Money Tracking**: MF holdings analysis with quarterly trends and institutional ownership
- **RBI Macro Data**: Real-time macroeconomic data from RBI (policy rates, inflation, GDP)
- **Screener.in Integration**: Financial statement extraction, ratios, and shareholding data
- **NSE API Integration**: Unofficial NSE endpoints for quotes, corporate announcements, FII/DII data
- **Unified Data Services Layer**: Single interface for all data sources with caching
- **Comprehensive Test Suite**: Unit tests, integration tests, and CI/CD pipeline
- **Reinforcement Learning**: Feedback system for continuous strategy improvement
- **Self-Improving AI**: Genetic algorithm for automated strategy generation, backtesting, and evolution

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

5. Install test dependencies (optional):

```bash
pip install -r requirements-test.txt
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
│  ┌──────────────────┐  ┌──────────────────────────────┐   │
│  │ Unified Data     │  │ Agent System                 │   │
│  │ Services Layer   │  │                              │   │
│  │                  │  │ ┌────────┐ ┌────────┐      │   │
│  │ - NSE API       │  │ │Technical│ │Sentiment│      │   │
│  │ - Screener.in   │  │ │Agents  │ │Agents  │      │   │
│  │ - RBI Macro     │  │ ├────────┤ ├────────┤      │   │
│  │ - AMFI MF      │  │ │Fundamen│ │Risk    │      │   │
│  │ - MF Holdings  │  │ │tal     │ │Agents  │      │   │
│  │ - Caching      │  │ └────────┘ └────────┘      │   │
│  └──────────────────┘  └──────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────┐   │
│  │ Signal Aggregator│  │ Portfolio Engine               │   │
│  │                  │  │                              │   │
│  │ - Weighted scores│  │ - Position sizing            │   │
│  │ - Regime-based   │  │ - Risk management            │   │
│  │ - Confidence    │  │ - Stop-loss/take-profit      │   │
│  └──────────────────┘  └──────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────┐   │
│  │ Backtest Engine  │  │ Self-Improving AI             │   │
│  │                  │  │                              │   │
│  │ - Historical sim │  │ - Strategy generation         │   │
│  │ - Metrics        │  │ - Genetic algorithm          │   │
│  │ - Equity curves  │  │ - Evolution engine           │   │
│  └──────────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Agent Categories

| Category | Description | Agents |
|----------|-------------|--------|
| **Technical** | Price/volume analysis | RSI, MACD, Momentum, Trend, Breakout, Volume |
| **Sentiment** | Market mood analysis | News Sentiment, Analyst Ratings |
| **Fundamental** | Financial metrics | CRISIL Analysis, Valuation, Earnings, Cashflow, Growth |
| **Risk** | Risk assessment | Volatility Regime, Tail Risk, India VIX |
| **Market Structure** | F&O data | FNO, Nifty Sentiment |
| **Institutional** | Smart money tracking | MF Holdings |

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
│   ├── regime_classifier.py   # Market regime classification
│   ├── technical/             # Technical analysis agents
│   │   ├── rsi_agent.py
│   │   ├── macd_agent.py
│   │   ├── momentum_agent.py
│   │   ├── trend_agent.py
│   │   ├── volume_agent.py
│   │   └── breakout_agent.py
│   ├── sentiment/             # Sentiment analysis agents
│   │   ├── news_sentiment_agent.py
│   │   └── analyst_rating_agent.py
│   ├── fundamental/          # Fundamental analysis agents
│   │   ├── valuation_agent.py
│   │   ├── earnings_agent.py
│   │   ├── cashflow_agent.py
│   │   ├── growth_agent.py
│   │   └── crisil_agent.py
│   ├── risk/                 # Risk management agents
│   │   ├── volatility_regime_agent.py
│   │   └── tail_risk_agent.py
│   └── india/                 # India-specific agents
│       ├── nifty_sentiment_agent.py
│       ├── mf_holdings_agent.py
│       ├── fno_agent.py
│       └── india_vix_agent.py
├── config/
│   └── settings.py           # Configuration settings
├── data/
│   ├── __init__.py          # Data module exports
│   ├── services.py          # Unified Data Services Layer
│   └── ingestion/            # Data ingestion modules
│       ├── __init__.py
│       ├── india_data.py     # Indian market data (NSE)
│       ├── nse_api.py       # NSE India async API client
│       ├── nse_api_client.py # NSE India API (unofficial endpoints)
│       ├── screener_data.py  # Screener.in financial data
│       ├── rbi_macro.py     # RBI macroeconomic data
│       ├── mf_data.py       # Mutual fund holdings
│       └── market_data.py   # Generic market data
├── signals/
│   ├── signal_schema.py     # Signal data structures
│   └── signal_aggregator.py # Signal aggregation logic
├── orchestration/
│   └── dispatcher.py        # Agent orchestration
├── ingestion/
│   └── mf/                 # MF data ingestion engine
│       ├── engine.py        # Main MF data engine
│       ├── models.py       # MF data models
│       ├── sources/        # Data sources
│       │   ├── amfi_source.py         # AMFI NAV & holdings
│       │   ├── mfapi_source.py
│       │   └── valueresearch_scraper.py
│       └── utils/
│           └── parser.py
├── learning/
│   ├── feedback_system.py     # RL feedback for agent weights
│   ├── strategy_generator.py  # Strategy template generation
│   ├── strategy_evaluator.py  # Backtesting and metrics
│   ├── evolution_engine.py   # Genetic algorithm engine
│   └── self_improving_system.py # Main orchestration
├── backtesting/
│   └── engine.py           # Backtesting engine
├── portfolio/
│   └── portfolio_engine.py # Portfolio management
├── features/
│   └── indicators.py       # Technical indicators
├── tests/                  # Test suite
│   ├── conftest.py         # Shared fixtures
│   ├── unit/               # Unit tests
│   │   ├── test_agents/
│   │   ├── test_signals/
│   │   ├── test_data/
│   │   ├── test_features/
│   │   ├── test_portfolio/
│   │   └── test_config/
│   └── integration/         # Integration tests
├── .github/
│   └── workflows/
│       └── test.yml        # CI/CD pipeline
├── pytest.ini              # Pytest configuration
├── requirements.txt       # Production dependencies
└── requirements-test.txt  # Test dependencies
```

## Mutual Fund Data Engine

The system includes a comprehensive MF data ingestion engine for smart money analysis:

### Data Sources

- **AMFI**: Official NAV data from Association of Mutual Funds in India
- **MFAPI**: Historical NAV data with returns calculation
- **ValueResearch**: Portfolio holdings (may be blocked by rate limiting)

### Features

- Stock-level MF holdings aggregation
- Top fund holder tracking
- Monthly/quarterly trend analysis
- Smart money signal generation
- Simulated data for demonstration when sources are blocked

### Usage

```python
from ingestion.mf.engine import mf_data_engine

# Get MF holdings for a stock
holdings = mf_data_engine.get_stock_mf_holdings("RELIANCE")
print(f"MFs holding: {holdings.num_mfs}")
print(f"Ownership: {holdings.mf_holding_pct}%")

# Generate MF buying signal
signal = mf_data_engine.analyze_stock_mf_signal("RELIANCE")
print(f"Signal: {signal.signal}, Confidence: {signal.confidence}")
```

## Unified Data Services Layer

The system provides a unified data services layer that aggregates all data sources:

### Features

- Single interface for all data sources
- Built-in caching with configurable TTL
- Automatic fallback mechanisms
- Batch fetching support

### Data Sources

- **NSE India**: Quotes, corporate announcements, FII/DII trading data
- **Screener.in**: Financial statements, ratios, shareholding patterns
- **RBI**: Macro economic data (policy rates, inflation, GDP, reserves)
- **AMFI**: Mutual fund NAVs and stock holdings
- **MF Holdings**: Institutional ownership analysis

### Usage

```python
from data import unified_data_service, get_stock_data, get_market_dashboard

# Get complete stock analysis
data = await get_stock_data("RELIANCE")

# Get market dashboard (macro + indices + FII/DII)
dashboard = await get_market_dashboard()

# Get specific data
quote = await unified_data_service.get_stock_quote("RELIANCE")
financials = await unified_data_service.get_stock_financials("RELIANCE")
macro = unified_data_service.get_macro_data()

# Direct data access
from data.ingestion import (
    get_quote,           # NSE quotes
    get_fiidii,          # FII/DII data
    get_financials,      # Screener.in financials
    get_ratios,          # Key ratios
    get_macro_snapshot,   # RBI macro data
    amfi_source,         # AMFI NAV data
)
```

## Self-Improving Quant AI System

The system includes a self-improving AI module that automatically generates, tests, and evolves trading strategies using genetic algorithms.

### Components

- **Strategy Generator**: Creates diverse trading strategies using templates (momentum, mean_reversion, breakout, trend_following)
- **Strategy Evaluator**: Backtesting engine with full metrics (Sharpe, Sortino, Calmar, max drawdown)
- **Evolution Engine**: Genetic algorithm with tournament selection, elite preservation, crossover, and mutation
- **Self-Improving System**: Orchestrates the entire pipeline - scrape data → generate → backtest → evolve → archive

### Usage

```bash
# Run strategy evolution
python -m learning.self_improving_system --symbols RELIANCE,HDFCBANK --generations 10 --population 20

# Parameters
# --symbols: Comma-separated stock symbols
# --population: Population size (default: 20)
# --generations: Number of generations (default: 10)
# --mutation: Mutation rate (default: 0.15)
```

### Programmatic Usage

```python
from learning.self_improving_system import SelfImprovingQuantSystem, SystemConfig

# Configure the system
config = SystemConfig(
    symbols=['RELIANCE', 'HDFCBANK', 'INFY'],
    population_size=20,
    generations=10,
    min_fitness=0.3
)

# Create and run evolution
system = SelfImprovingQuantSystem(config)

def progress(gen, total, fitness):
    print(f"Generation {gen + 1}/{total}: Best Fitness = {fitness:.4f}")

result = system.evolve_strategies(progress_callback=progress)

# Get best strategy
best = result.best_strategy
print(f"Best: {best.name}, Return: {result.best_result.total_return:.2%}")
```

### Learning Modules

```
learning/
├── feedback_system.py          # RL feedback for agent weight optimization
├── strategy_generator.py       # Strategy template generation
├── strategy_evaluator.py      # Backtesting and metrics
├── evolution_engine.py        # Genetic algorithm engine
└── self_improving_system.py   # Main orchestration
```

## Testing

The project includes a comprehensive test suite with unit tests, integration tests, and CI/CD automation.

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                   # Unit tests
│   ├── test_agents/       # Agent tests (base, RSI, MACD, etc.)
│   ├── test_signals/      # Signal schema and aggregator tests
│   ├── test_data/         # Data ingestion tests
│   ├── test_features/     # Technical indicators tests
│   ├── test_portfolio/    # Portfolio engine tests
│   └── test_config/       # Configuration tests
└── integration/            # End-to-end integration tests
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
cd quant-agent-trader
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test category
pytest tests/unit/test_agents/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with markers
pytest -m "not slow"  # Skip slow tests
```

### Coverage Targets

| Module | Target |
|--------|--------|
| agents/ | 85% |
| signals/ | 90% |
| features/ | 85% |
| portfolio/ | 80% |
| data/ | 75% |
| config/ | 90% |

### CI/CD Pipeline

The project uses GitHub Actions for automated testing:

- **Test Job**: Runs unit and integration tests with coverage
- **Lint Job**: Code quality checks with ruff and mypy
- **Security Job**: Vulnerability scanning with safety and bandit

The workflow runs on:
- Every push to main/develop branches
- Every pull request to main branch

## Troubleshooting

### Common Issues

1. **No data fetched**: Check internet connection or set API keys
2. **Agent errors**: Some agents may fail if required features are missing
3. **Import errors**: Ensure all dependencies are installed
4. **Memory issues**: Reduce `max_concurrent_agents` in config
5. **ValueResearch 403 errors**: The scraper may be blocked; system uses simulated data
6. **NIFTY BANK symbol errors**: Use ^NSEBANK instead of ^NSEB
7. **Test import errors**: Install test dependencies with `pip install -r requirements-test.txt`
8. **Coverage below target**: Run `pytest --cov=. --cov-report=term-missing` to see uncovered lines

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
