"""
Quant Agent Trader - Configuration Settings
Production-grade configuration management for the multi-agent trading system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
# Get optimal worker count based on CPU cores
def _get_optimal_workers() -> int:
    """Get optimal worker count based on CPU cores."""
    try:
        import multiprocessing
        cpu_count = os.cpu_count() or 4
        # Optimal: min(cpu_count * 2, 32) for CPU-bound tasks - increased for more agents
        return min(cpu_count * 2, 32)
    except Exception:
        return 16

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"


@dataclass
class DataConfig:
    """Market data source configurations."""
    polygon_api_key: str = ""  # Optional - using NSE India API now
    alpha_vantage_key: str = ""  # Optional
    cache_ttl: int = 300  # seconds
    max_retries: int = 3
    rate_limit_delay: float = 0.1


@dataclass
class AgentConfig:
    """Agent execution configurations."""
    max_concurrent_agents: int = field(default_factory=_get_optimal_workers)
    agent_timeout: int = 30  # seconds
    enable_caching: bool = True
    cache_ttl: int = 3600
    retry_failed: bool = True
    max_retries: int = 2


@dataclass
class SignalConfig:
    """Signal aggregation configurations."""
    weights: Dict[str, float] = field(default_factory=lambda: {
        "technical": 0.30,
        "fundamental": 0.25,
        "sentiment": 0.15,
        "macro": 0.10,
        "market_structure": 0.10,
        "risk": 0.10
    })
    min_confidence_threshold: float = 0.5
    signal_normalization: bool = True


@dataclass
class PortfolioConfig:
    """Portfolio management configurations."""
    max_position_size: float = 0.10  # 10% max per position
    default_position_size: float = 0.05  # 5% default
    max_portfolio_stocks: int = 20
    rebalance_threshold: float = 0.15
    risk_per_trade: float = 0.02  # 2% risk per trade
    holdings_csv_path: str = os.getenv("HOLDINGS_CSV_PATH", "C:\\Users\\Harshil\\Desktop\\holdings.csv")
    trades_csv_path: str = os.getenv("TRADES_CSV_PATH", "C:\\Users\\Harshil\\Desktop\\trades.csv")
    daily_holdings_dir: str = os.getenv("DAILY_HOLDINGS_DIR", "data/daily_holdings")


@dataclass
class BacktestConfig:
    """Backtesting configurations."""
    initial_capital: float = 100000.0
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    benchmark: str = "SPY"


@dataclass
class RLConfig:
    """Reinforcement learning configurations."""
    learning_rate: float = 0.01
    discount_factor: float = 0.95
    exploration_rate: float = 0.1
    memory_size: int = 10000
    batch_size: int = 32
    update_frequency: int = 100


# Indian Market Configuration
INDIA_MARKET_HOURS = {
    "timezone": "Asia/Kolkata",
    "session_start": "09:15:00",
    "session_end": "15:30:00",
    "pre_market_start": "09:00:00",
    "closing_auction": "15:40:00",
}

INDIA_NSE_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR", "ICICIBANK",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "HCLTECH", "ASIANPAINT",
    "MARUTI", "TITAN", "BAJFINANCE", "WIPRO", "ULTRACEMCO", "NTPC",
    "POWERGRID", "M&M", "SUNPHARMA", "TATASTEEL", "DRREDDY", "CIPLA",
    "ADANIPORTS", "BAJAJFINSV", "GRASIM", "HEROMOTOCO", "INDUSINDBK",
    "JSWSTEEL", "SBILIFE", "SHREECEM", "AXISBANK", "ADANIENT", "DIVISLAB",
]

INDIA_BSE_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "HINDUNILVR", "ICICIBANK",
    "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "HCLTECH", "ASIANPAINT",
]

INDIA_INDICES = {
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEB",
    "NIFTY IT": "^CNXIT",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY ENERGY": "^CNXENERGY",
    "NIFTY REALTY": "^CNXREALTY",
    "INDIA VIX": "^INDIAVIX",
}

INDIA_FNO_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "KOTAKBANK",
    "LT", "HINDUNILVR", "SBIN", "BHARTIARTL", "BAJFINANCE", "M&M",
    "TATASTEEL", "SUNPHARMA", "WIPRO", "HCLTECH", "ASIANPAINT", "AXISBANK",
]

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

INDIA_TRADING_RULES = {
    "lot_sizes": {
        "RELIANCE": 1, "TCS": 1, "HDFCBANK": 1, "INFY": 1,
        "HINDUNILVR": 1, "ICICIBANK": 1, "SBIN": 1, "BHARTIARTL": 1,
        "KOTAKBANK": 1, "LT": 1, "BAJFINANCE": 1,
    },
    "tick_size": 0.05,
    "max_order_size": 1000000,
    "price_band_limits": {
        "normal": 5.0,
        "lower_circuit": 5.0,
        "upper_circuit": 5.0,
    },
    "brokerage_rate": 0.001,
    "stt_rate": 0.001,
    "sebi_charges": 0.00015,
    "stamp_duty": 0.002,
    "gst": 0.18,
}


@dataclass
class IndiaConfig:
    """India-specific market configuration."""
    enable_india_mode: bool = True
    use_nse: bool = True
    use_bse: bool = False
    include_fno: bool = True
    include_india_vix: bool = True
    default_currency: str = "INR"
    nse_holidays: List[str] = field(default_factory=lambda: [
        "2024-01-26", "2024-03-08", "2024-03-25", "2024-04-11",
        "2024-05-01", "2024-06-17", "2024-07-17", "2024-08-15",
        "2024-10-02", "2024-11-01", "2024-11-15", "2024-12-25",
    ])


@dataclass
class SystemConfig:
    """Main system configuration."""
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = "INFO"
    enable_distributed: bool = False
    ray_address: str = "auto"
    use_kafka: bool = False
    kafka_bootstrap_servers: str = "localhost:9092"
    
    # Data config
    data: DataConfig = field(default_factory=DataConfig)
    
    # Agent config
    agents: AgentConfig = field(default_factory=AgentConfig)
    
    # Signal config
    signals: SignalConfig = field(default_factory=SignalConfig)
    
    # Portfolio config
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    
    # Backtest config
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    
    # RL config
    rl: RLConfig = field(default_factory=RLConfig)
    
    # India config
    india: IndiaConfig = field(default_factory=IndiaConfig)


# Regime-based weight adjustments
REGIME_WEIGHTS = {
    "bull": {
        "technical": 0.35,
        "fundamental": 0.25,
        "sentiment": 0.15,
        "macro": 0.10,
        "market_structure": 0.10,
        "risk": 0.05
    },
    "bear": {
        "technical": 0.15,
        "fundamental": 0.30,
        "sentiment": 0.10,
        "macro": 0.15,
        "market_structure": 0.10,
        "risk": 0.20
    },
    "sideways": {
        "technical": 0.20,
        "fundamental": 0.25,
        "sentiment": 0.15,
        "macro": 0.10,
        "market_structure": 0.15,
        "risk": 0.15
    },
    "high_volatility": {
        "technical": 0.20,
        "fundamental": 0.20,
        "sentiment": 0.15,
        "macro": 0.10,
        "market_structure": 0.10,
        "risk": 0.25
    }
}


# Agent category definitions
AGENT_CATEGORIES = {
    "technical": [
        "rsi_agent", "macd_agent", "momentum_agent", "trend_agent",
        "moving_average_agent", "breakout_agent", "support_resistance_agent",
        "bollinger_agent", "atr_agent", "volume_profile_agent",
        "ichimoku_agent", "williams_r_agent", "cci_agent", "adx_agent",
        "obv_agent", "vwap_agent", "mfi_agent", "keltner_agent", "donchian_agent"
    ],
    "fundamental": [
        "valuation_agent", "earnings_agent", "cashflow_agent",
        "balance_sheet_agent", "growth_agent", "dividend_agent",
        "industry_comparison_agent", "management_quality_agent"
    ],
    "sentiment": [
        "news_sentiment_agent", "social_sentiment_agent",
        "analyst_rating_agent", "insider_trading_agent", "institutional_flow_agent"
    ],
    "macro": [
        "interest_rate_agent", "inflation_agent", "gdp_agent",
        "sector_rotation_agent", "currency_agent", "commodity_agent"
    ],
    "market_structure": [
        "options_flow_agent", "dark_pool_agent", "order_imbalance_agent",
        "liquidity_agent", "volatility_surface_agent", "put_call_ratio_agent"
    ],
    "risk": [
        "volatility_regime_agent", "tail_risk_agent", "drawdown_agent",
        "correlation_risk_agent", "liquidity_risk_agent", "credit_risk_agent"
    ],
    "quant": [
        "mean_reversion_agent", "stat_arb_agent", "factor_model_agent",
        "pairs_trading_agent", "momentum_factor_agent", "value_factor_agent"
    ],
    "india": [
        "india_vix_agent", "fno_agent", "nifty_sentiment_agent"
    ],
    "meta": [
        "reliability_scoring_agent", "regime_classification_agent",
        "correlation_detection_agent", "ensemble_optimization_agent"
    ]
}


# Create global config instance
config = SystemConfig()
