"""
Quant Agent Trader - Main Entry Point

Multi-agent quantitative trading system with parallel agent execution,
signal aggregation, and portfolio management.

Usage:
    python main.py analyze --symbol AAPL
    python main.py backtest --symbols AAPL,GOOGL --start 2023-01-01 --end 2024-01-01
    python main.py live --symbols AAPL,MSFT
"""

import argparse
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import pandas as pd
import numpy as np

load_dotenv()

from config.settings import (
    config as system_config,
    SystemConfig,
    DataConfig,
    AgentConfig,
    SignalConfig,
    PortfolioConfig,
    BacktestConfig,
    INDIA_NSE_SYMBOLS,
    INDIA_INDICES,
    INDIA_TRADING_RULES,
)
from data.ingestion.market_data import DataIngestionEngine, MockDataSource
from data.ingestion.india_data import india_data_engine, IndiaDataSource, NSE_SYMBOLS
from ingestion.mf.engine import mf_data_engine
from signals.signal_schema import AgentSignal, AggregatedSignal, PortfolioDecision
from signals.signal_aggregator import SignalAggregator
from orchestration.dispatcher import AgentDispatcher, DispatcherConfig
from agents.base_agent import BaseAgent, AgentRegistry, AgentConfig as BaseAgentConfig
from agents.technical.rsi_agent import RSIAgent
from agents.technical.macd_agent import MACDAgent
from agents.technical.momentum_agent import MomentumAgent
from agents.technical.trend_agent import TrendAgent
from agents.technical.breakout_agent import BreakoutAgent
from agents.technical.volume_agent import VolumeAgent
from agents.technical.bollinger_agent import BollingerAgent
from agents.technical.atr_agent import ATRAgent
from agents.technical.support_resistance_agent import SupportResistanceAgent
from agents.technical.volume_profile_agent import VolumeProfileAgent
from agents.technical.ichimoku_agent import IchimokuAgent
from agents.technical.williams_r_agent import WilliamsRAgent
from agents.technical.cci_agent import CCIAgent
from agents.technical.adx_agent import ADXAgent
from agents.technical.obv_agent import OBVAgent
from agents.technical.vwap_agent import VWAPAgent
from agents.technical.mfi_agent import MFIAgent
from agents.technical.keltner_agent import KeltnerAgent
from agents.technical.donchian_agent import DonchianAgent
from agents.fundamental.valuation_agent import ValuationAgent
from agents.fundamental.dividend_agent import DividendAgent
from agents.fundamental.balance_sheet_agent import BalanceSheetAgent
from agents.fundamental.industry_comparison_agent import IndustryComparisonAgent
from agents.fundamental.management_quality_agent import ManagementQualityAgent
from agents.sentiment.insider_trading_agent import InsiderTradingAgent
from agents.sentiment.social_sentiment_agent import SocialSentimentAgent
from agents.risk.drawdown_agent import DrawdownAgent
from agents.risk.correlation_risk_agent import CorrelationRiskAgent
from agents.macro.interest_rate_agent import InterestRateAgent
from agents.macro.inflation_agent import InflationAgent
from agents.macro.gdp_agent import GDPAgent
from agents.macro.sector_rotation_agent import SectorRotationAgent
from agents.macro.currency_agent import CurrencyAgent
from agents.macro.commodity_agent import CommodityAgent
from agents.market_structure.options_flow_agent import OptionsFlowAgent
from agents.market_structure.dark_pool_agent import DarkPoolAgent
from agents.market_structure.order_imbalance_agent import OrderImbalanceAgent
from agents.market_structure.put_call_ratio_agent import PutCallRatioAgent
from agents.quant.mean_reversion_agent import MeanReversionAgent
from agents.quant.stat_arb_agent import StatArbAgent
from agents.quant.factor_model_agent import FactorModelAgent
from agents.quant.pairs_trading_agent import PairsTradingAgent
from agents.india.india_vix_agent import IndiaVIXAgent
from agents.india.fno_agent import FNOAgent
from agents.india.nifty_sentiment_agent import NiftySentimentAgent
from agents.india.mf_holdings_agent import MFHoldingsAgent, MFHoldingsAnalyzer
from agents.fundamental.crisil_agent import (
    CRISILAnalysisAgent,
    CRISILDataEngine,
    crisil_engine,
)
from agents.fundamental.valuation_agent import ValuationAgent
from backtesting.engine import BacktestEngine, BacktestConfigExtended
from features.indicators import TechnicalFeatures


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("quant_trader.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


def _is_indian_symbol(symbol: str) -> bool:
    """Check if symbol is Indian market (NSE/BSE)."""
    upper = symbol.upper()
    return (
        upper in NSE_SYMBOLS
        or upper in INDIA_NSE_SYMBOLS
        or upper in INDIA_INDICES
        or symbol.endswith(".NS")
        or symbol.endswith(".BO")
    )


class QuantTradingSystem:
    """
    Main quant trading system orchestrating all components.
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or system_config
        self.dispatcher: Optional[AgentDispatcher] = None
        self.aggregator: SignalAggregator = SignalAggregator()
        self.data_engine: Optional[DataIngestionEngine] = None
        self.backtest_engine: BacktestEngine = BacktestEngine()
        self.agents: List[BaseAgent] = []
        self._initialize()

    def _initialize(self) -> None:
        logger.info("Initializing Quant Trading System...")

        self._initialize_data_engine()
        self._initialize_agents()
        self._initialize_dispatcher()

        logger.info(f"Initialized with {len(self.agents)} agents")

    def _initialize_data_engine(self) -> None:
        data_config = {
            "polygon_api_key": self.config.data.polygon_api_key,
            "alpha_vantage_key": self.config.data.alpha_vantage_key,
        }

        if data_config["polygon_api_key"] or data_config["alpha_vantage_key"]:
            self.data_engine = DataIngestionEngine(data_config)
            logger.info("Data engine initialized with API sources")
        else:
            if self.config.data.has_upstox_keys():
                logger.info("Upstox API configured - using Indian market data")
            else:
                logger.warning(
                    "No US API keys found, using fallback (yfinance for India)"
                )

    def _initialize_agents(self) -> None:
        agent_base_config = BaseAgentConfig(
            enable_cache=self.config.agents.enable_caching,
            cache_ttl_seconds=self.config.agents.cache_ttl,
            timeout_seconds=self.config.agents.agent_timeout,
            max_retries=self.config.agents.max_retries,
        )

        # Technical agents
        self.agents = [
            RSIAgent(config=agent_base_config),
            MACDAgent(config=agent_base_config),
            MomentumAgent(config=agent_base_config),
            TrendAgent(config=agent_base_config),
            BreakoutAgent(config=agent_base_config),
            VolumeAgent(config=agent_base_config),
            BollingerAgent(config=agent_base_config),
            ATRAgent(config=agent_base_config),
            SupportResistanceAgent(config=agent_base_config),
            VolumeProfileAgent(config=agent_base_config),
            IchimokuAgent(config=agent_base_config),
            WilliamsRAgent(config=agent_base_config),
            CCIAgent(config=agent_base_config),
            ADXAgent(config=agent_base_config),
            OBVAgent(config=agent_base_config),
            VWAPAgent(config=agent_base_config),
            MFIAgent(config=agent_base_config),
            KeltnerAgent(config=agent_base_config),
            DonchianAgent(config=agent_base_config),
        ]

        # Fundamental agents
        self.agents.extend(
            [
                DividendAgent(config=agent_base_config),
                BalanceSheetAgent(config=agent_base_config),
                IndustryComparisonAgent(config=agent_base_config),
                ManagementQualityAgent(config=agent_base_config),
            ]
        )

        # Sentiment agents
        self.agents.extend(
            [
                InsiderTradingAgent(config=agent_base_config),
                SocialSentimentAgent(config=agent_base_config),
            ]
        )

        # Risk agents
        self.agents.extend(
            [
                DrawdownAgent(config=agent_base_config),
                CorrelationRiskAgent(config=agent_base_config),
            ]
        )

        # Macro agents
        self.agents.extend(
            [
                InterestRateAgent(config=agent_base_config),
                InflationAgent(config=agent_base_config),
                GDPAgent(config=agent_base_config),
                SectorRotationAgent(config=agent_base_config),
                CurrencyAgent(config=agent_base_config),
                CommodityAgent(config=agent_base_config),
            ]
        )

        # Market Structure agents
        self.agents.extend(
            [
                OptionsFlowAgent(config=agent_base_config),
                DarkPoolAgent(config=agent_base_config),
                OrderImbalanceAgent(config=agent_base_config),
                PutCallRatioAgent(config=agent_base_config),
            ]
        )

        # Quant agents
        self.agents.extend(
            [
                MeanReversionAgent(config=agent_base_config),
                StatArbAgent(config=agent_base_config),
                FactorModelAgent(config=agent_base_config),
                PairsTradingAgent(config=agent_base_config),
            ]
        )

        # Add fundamental agents (CRISIL, Valuation)
        try:
            self.agents.append(CRISILAnalysisAgent(config=agent_base_config))
            self.agents.append(ValuationAgent(config=agent_base_config))
            logger.info("Added CRISIL and Valuation agents")
        except Exception as e:
            logger.warning(f"Could not add CRISIL/Valuation agents: {e}")

        # Add MF holdings agent for Indian stocks
        try:
            self.agents.append(MFHoldingsAgent(config=agent_base_config))
            logger.info("Added MF Holdings agent")
        except Exception as e:
            logger.warning(f"Could not add MF Holdings agent: {e}")

        logger.info(f"Initialized {len(self.agents)} total agents")

    def _initialize_dispatcher(self) -> AgentDispatcher:
        if not self.agents:
            raise RuntimeError("Agents must be initialized before dispatcher")

        dispatcher_config = DispatcherConfig(
            max_workers=self.config.agents.max_concurrent_agents,
            timeout_seconds=self.config.agents.agent_timeout,
            enable_ray=False,
            enable_retry=self.config.agents.retry_failed,
            max_retries=self.config.agents.max_retries,
        )

        self.dispatcher = AgentDispatcher(config=dispatcher_config)
        logger.info(f"Dispatcher created: {self.dispatcher}")

        self.dispatcher.register_agents(self.agents)

        logger.info(f"Dispatcher initialized with {len(self.agents)} agents")
        return self.dispatcher

    async def fetch_market_data(self, symbol: str, days: int = 365) -> pd.DataFrame:
        if _is_indian_symbol(symbol):
            df = await india_data_engine.get_price_data(
                symbol=symbol, timeframe="1d", limit=days
            )
            if df is not None:
                return df

        if self.data_engine:
            df = await self.data_engine.get_price_data(
                symbol=symbol, timeframe="daily", limit=days
            )
            if df is not None:
                return df

        mock_source = MockDataSource()
        df = await mock_source.get_price_data(symbol, limit=days)
        return df

    async def get_india_vix_data(self, days: int = 30) -> Dict[str, Any]:
        """Get India VIX data for VIX agent."""
        vix_df = await india_data_engine.get_india_vix(limit=days)

        if vix_df is None or vix_df.empty:
            return {}

        vix_values = vix_df["close"].tolist() if "close" in vix_df.columns else []

        return {
            "india_vix": vix_values[-1] if vix_values else None,
            "india_vix_history": vix_values,
        }

    async def get_nifty_sentiment_data(self) -> Dict[str, Any]:
        """Get NIFTY sentiment data for NiftySentimentAgent."""
        import random

        nifty_data = {}

        try:
            nifty_df = await india_data_engine.get_price_data(
                "NIFTY 50", timeframe="1d", limit=60
            )
            if nifty_df is not None and not nifty_df.empty:
                nifty_data["nifty_price"] = float(nifty_df.iloc[-1]["close"])
                nifty_change = (
                    (nifty_df.iloc[-1]["close"] - nifty_df.iloc[0]["close"])
                    / nifty_df.iloc[0]["close"]
                ) * 100
                nifty_data["nifty_change"] = nifty_change

                if "sma50" in nifty_df.columns or "sma_50" in nifty_df.columns:
                    sma_col = "sma50" if "sma50" in nifty_df.columns else "sma_50"
                    current_price = nifty_df.iloc[-1]["close"]
                    nifty_data["nifty_above_sma50"] = (
                        1.0 if current_price > nifty_df.iloc[-1][sma_col] else 0.0
                    )
                else:
                    nifty_data["nifty_above_sma50"] = random.choice(
                        [0.45, 0.55, 0.60, 0.50, 0.40]
                    )

                if "sma200" in nifty_df.columns or "sma_200" in nifty_df.columns:
                    sma_col = "sma200" if "sma200" in nifty_df.columns else "sma_200"
                    current_price = nifty_df.iloc[-1]["close"]
                    nifty_data["nifty_above_sma200"] = (
                        1.0 if current_price > nifty_df.iloc[-1][sma_col] else 0.0
                    )
                else:
                    nifty_data["nifty_above_sma200"] = random.choice(
                        [0.45, 0.55, 0.60, 0.50, 0.40]
                    )
        except Exception as e:
            logger.warning(f"Error fetching NIFTY 50 data: {e}")
            nifty_data["nifty_price"] = 22500.0
            nifty_data["nifty_change"] = 0.0
            nifty_data["nifty_above_sma50"] = 0.5
            nifty_data["nifty_above_sma200"] = 0.5

        try:
            nifty_bank_df = await india_data_engine.get_price_data(
                "NIFTY BANK", timeframe="1d", limit=60
            )
            if nifty_bank_df is not None and not nifty_bank_df.empty:
                nifty_data["nifty_bank_price"] = float(nifty_bank_df.iloc[-1]["close"])
                bank_change = (
                    (nifty_bank_df.iloc[-1]["close"] - nifty_bank_df.iloc[0]["close"])
                    / nifty_bank_df.iloc[0]["close"]
                ) * 100
                nifty_data["nifty_bank_change"] = bank_change
            else:
                nifty_data["nifty_bank_price"] = 48000.0
                nifty_data["nifty_bank_change"] = nifty_data.get("nifty_change", 0.0)
        except Exception as e:
            logger.warning(f"Error fetching NIFTY BANK data: {e}")
            nifty_data["nifty_bank_price"] = 48000.0
            nifty_data["nifty_bank_change"] = nifty_data.get("nifty_change", 0.0)

        nifty_data["advances"] = random.randint(25, 35)
        nifty_data["declines"] = random.randint(15, 25)

        nifty_data["sector_performance"] = {
            "NIFTY AUTO": random.uniform(-2.0, 2.0),
            "NIFTY BANK": random.uniform(-1.5, 2.0),
            "NIFTY IT": random.uniform(-2.5, 1.5),
            "NIFTY FMCG": random.uniform(-1.0, 1.0),
            "NIFTY METAL": random.uniform(-3.0, 2.5),
            "NIFTY PHARMA": random.uniform(-1.5, 1.5),
            "NIFTY ENERGY": random.uniform(-2.0, 2.0),
            "NIFTY REALTY": random.uniform(-2.5, 2.5),
        }

        return nifty_data

    async def get_fno_data(self, symbol: str) -> Dict[str, Any]:
        """Get F&O data for FNOAgent. Uses mock data since live F&O requires paid APIs."""
        import random

        fno_data = {}

        current_price = 0.0
        if symbol.upper() in INDIA_NSE_SYMBOLS:
            try:
                quote = await india_data_engine.get_quote(symbol)
                if quote:
                    current_price = float(quote.get("price", 0))
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid price data for {symbol}: {e}")
            except Exception as e:
                logger.error(f"Failed to get quote for {symbol}: {e}")

        if current_price == 0:
            current_price = random.uniform(1000, 5000)

        futures_price = current_price * random.uniform(0.99, 1.02)

        fno_data["price"] = current_price
        fno_data["futures_price"] = futures_price
        fno_data["open_interest"] = random.randint(1000000, 5000000)
        fno_data["volume"] = random.randint(500000, 2000000)
        fno_data["put_call_ratio"] = random.uniform(0.8, 1.4)
        fno_data["oi_change"] = random.uniform(-15, 25)
        fno_data["fii_activity"] = random.uniform(-5000, 8000)
        fno_data["fii_buy"] = random.uniform(1000, 5000)
        fno_data["fii_sell"] = random.uniform(1000, 5000)

        return fno_data

    async def get_mf_holdings_data(self, symbol: str) -> Dict[str, Any]:
        """Get MF holdings data for Indian stock using new MF engine."""
        try:
            # Use new MF data engine (synchronous)
            holdings_data = mf_data_engine.get_stock_mf_holdings(symbol)

            # Get FII data using yfinance
            fii_data = await self._get_fii_data(symbol)

            # Generate analysis based on MF and FII data
            analysis = self._analyze_mf_fii(holdings_data, fii_data)

            # Convert to dict format for compatibility
            return {
                "mf": holdings_data.to_dict(),
                "fii": fii_data,
                "analysis": analysis,
            }
        except Exception as e:
            logger.warning(f"Error fetching MF data for {symbol}: {e}")
            return {}

    async def _get_fii_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch FII holdings data using yfinance."""
        try:
            import yfinance as yf

            ticker = yf.Ticker(f"{symbol}.NS")
            major_holders = ticker.major_holders

            fii_pct = 0.0
            fii_change = 0.0

            if major_holders is not None and not major_holders.empty:
                # Vectorized approach: find FII row using string contains
                holder_col = major_holders.iloc[:, 0].astype(str).str.lower()
                fii_mask = holder_col.str.contains("foreign|fii", regex=True, na=False)
                if fii_mask.any():
                    fii_row = major_holders[fii_mask].iloc[0]
                    pct = fii_row.iloc[1] if len(fii_row) > 1 else 0
                    if pct and not pd.isna(pct):
                        fii_pct = float(pct)

            # If no FII data found, use realistic defaults for demo
            if fii_pct == 0.0:
                import random

                fii_pct = round(random.uniform(15.0, 30.0), 2)
                fii_change = round(random.uniform(-2.0, 2.0), 2)

            return {
                "fii_holding_pct": fii_pct,
                "fii_change": fii_change,
                "symbol": symbol.upper(),
            }
        except Exception as e:
            logger.debug(f"FII data fetch failed for {symbol}: {e}")
            return {"fii_holding_pct": 0.0, "fii_change": 0.0, "symbol": symbol.upper()}

    def _analyze_mf_fii(self, mf_data, fii_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze MF and FII relationship to generate sentiment, smart_money, trend."""
        mf_pct = mf_data.mf_holding_pct
        mf_change = mf_data.change_in_holding
        fii_pct = fii_data.get("fii_holding_pct", 0.0)
        fii_change = fii_data.get("fii_change", 0.0)

        # Determine sentiment
        total_inst = mf_pct + fii_pct
        if mf_pct > 5 and mf_change > 0.3:
            sentiment = "Bullish (MF Accumulation)"
        elif fii_pct > 20 and fii_change > 0.5:
            sentiment = "Bullish (FII Inflow)"
        elif mf_pct > 5 and mf_change < -0.3:
            sentiment = "Bearish (MF Distribution)"
        elif fii_pct > 20 and fii_change < -0.5:
            sentiment = "Bearish (FII Outflow)"
        elif total_inst > 40:
            sentiment = "Neutral (High Institutional)"
        else:
            sentiment = "Neutral"

        # Determine smart money (who dominates)
        if mf_pct > fii_pct:
            smart_money = "MF Dominant"
        elif fii_pct > mf_pct:
            smart_money = "FII Dominant"
        else:
            smart_money = "Balanced"

        # Determine trend from monthly data
        if mf_data.monthly_trend:
            first_pct = mf_data.monthly_trend[0].get("mf_holding_pct", 0)
            last_pct = mf_data.monthly_trend[-1].get("mf_holding_pct", 0)
            if last_pct > first_pct * 1.1:
                trend = "Increasing"
            elif last_pct < first_pct * 0.9:
                trend = "Decreasing"
            else:
                trend = "Stable"
        else:
            if mf_change > 0.3:
                trend = "Increasing"
            elif mf_change < -0.3:
                trend = "Decreasing"
            else:
                trend = "Stable"

        return {"sentiment": sentiment, "smart_money": smart_money, "trend": trend}

    def prepare_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {}

        # Ensure lowercase columns for feature calculation
        df.columns = [c.lower() for c in df.columns]

        # Ensure required OHLC columns exist
        required = ["open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            logger.warning(f"Missing columns in data: {missing}")
            return {}

        if "rsi" not in df.columns:
            df = TechnicalFeatures.calculate_all(df)

        return TechnicalFeatures.get_current_features(df)

    async def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        logger.info(f"Analyzing stock: {symbol}")

        df = await self.fetch_market_data(symbol, days=365)

        if df is None or df.empty:
            return {"error": f"Failed to fetch data for {symbol}"}

        features = self.prepare_features(df)

        is_indian = _is_indian_symbol(symbol)

        mf_analysis = {}

        if is_indian:
            india_features = await self.get_india_vix_data()
            features.update(india_features)
            features["symbol"] = symbol.upper()

            nifty_sentiment_data = await self.get_nifty_sentiment_data()
            features.update(nifty_sentiment_data)

            if symbol.upper() in INDIA_NSE_SYMBOLS:
                quote = await india_data_engine.get_quote(symbol)
                if quote:
                    features["spot_price"] = quote.get("price")
                    features["futures_price"] = quote.get("price")
                    features["volume"] = quote.get("volume", 0)
                    features["put_call_ratio"] = 1.0

                fno_data = await self.get_fno_data(symbol)
                features.update(fno_data)

                # Fetch MF holdings data
                mf_analysis = await self.get_mf_holdings_data(symbol)

                if mf_analysis:
                    mf_data = mf_analysis.get("mf", {})
                    fii_data = mf_analysis.get("fii", {})

                    features["mf_num_holders"] = mf_data.get("num_mfs_holding", 0)
                    features["mf_holding_pct"] = mf_data.get("mf_holding_pct", 0.0)
                    features["mf_change"] = mf_data.get("change_in_holding", 0.0)
                    features["mf_top_holders"] = mf_data.get("top_mf_holders", [])
                    features["mf_monthly_trend"] = mf_data.get("monthly_trend", [])
                    features["fii_holding_pct"] = fii_data.get("fii_holding_pct", 0.0)
                    features["fii_change"] = fii_data.get("fii_change", 0.0)

                    # Enhanced MF features for v2.0 agent
                    features["mf_quarterly_change"] = (
                        mf_data.get("change_in_holding", 0.0) * 0.25
                    )  # Estimated quarterly
                    features["mf_new_additions"] = min(
                        5, mf_data.get("num_mfs_holding", 0) // 4
                    )  # Estimated
                    features["mf_net_flow"] = (
                        mf_data.get("change_in_holding", 0.0) * 100
                    )  # Estimated in Crores
                    features["mf_avg_flow"] = 100.0  # Default average
                    features["mf_yoy_change"] = (
                        mf_data.get("change_in_holding", 0.0) * 4
                    )  # Estimated YOY

                    # Top holder concentration
                    if mf_data.get("top_mf_holders"):
                        top_holder = mf_data["top_mf_holders"][0]
                        features["mf_top_holder_pct"] = top_holder.get("pct", 0.0)
                    else:
                        features["mf_top_holder_pct"] = 0.0

                # Fetch CRISIL data
                try:
                    from agents.fundamental.crisil_agent import crisil_engine

                    crisil_data = await crisil_engine.get_crisil_analysis(symbol)
                    features["crisil_rating"] = crisil_data.get("rating", "")
                    features["crisil_outlook"] = crisil_data.get("outlook", "stable")
                    features["industry_outlook"] = crisil_data.get(
                        "industry_outlook", "stable"
                    )
                    features["business_risk"] = crisil_data.get(
                        "business_risk", "moderate"
                    )
                    features["financial_risk"] = crisil_data.get(
                        "financial_risk", "moderate"
                    )
                    features["management_score"] = crisil_data.get(
                        "management_score", 50.0
                    )
                    features["corporate_governance_score"] = crisil_data.get(
                        "corporate_governance_score", 50.0
                    )
                except Exception as e:
                    logger.warning(f"Could not fetch CRISIL data: {e}")

                # Fetch valuation data (from yfinance)
                # try:
                #     import yfinance as yf
                #     ticker = yf.Ticker(f"{symbol}.NS" if is_indian else symbol)
                #     info = ticker.info

                #     features["pe_ratio"] = info.get("trailingPE", 0.0) or 0.0
                #     features["pb_ratio"] = info.get("priceToBook", 0.0) or 0.0
                #     features["ps_ratio"] = info.get("priceToSalesTrailing12Months", 0.0) or 0.0
                #     features["ev_ebitda"] = info.get("enterpriseToEbitda", 0.0) or 0.0
                #     features["dividend_yield"] = info.get("dividendYield", 0.0) or 0.0
                #     features["eps"] = info.get("trailingEps", 0.0) or 0.0
                #     features["book_value"] = info.get("bookValue", 0.0) or 0.0
                # except Exception as e:
                #     logger.warning(f"Could not fetch valuation data: {e}")

        current_price = float(df.iloc[-1]["close"])

        active_agents = self.agents.copy()

        if is_indian:
            from agents.base_agent import AgentConfig as BaseAgentConfig

            india_agent_config = BaseAgentConfig()
            vix_agent = IndiaVIXAgent(config=india_agent_config)
            fno_agent = FNOAgent(config=india_agent_config)
            sentiment_agent = NiftySentimentAgent(config=india_agent_config)

            # MF Holdings agent already added in self.agents, just add India-specific agents
            active_agents.extend([vix_agent, fno_agent, sentiment_agent])

        if self.dispatcher is None:
            raise RuntimeError("Dispatcher not initialized")

        dispatch_results = self.dispatcher.dispatch_agents(
            agents=active_agents,
            market_data={symbol: features},
            use_cache=True,
            aggregate=True,
        )

        results = dispatch_results.get(symbol, [])

        aggregated_signal = None
        agent_signals = []

        for result in results:
            if result.success and result.signal:
                if result.agent_name == "aggregated":
                    aggregated_signal = result.signal
                else:
                    agent_signals.append(result.signal)

        if not aggregated_signal and agent_signals:
            aggregated_signal = self.aggregator.aggregate_signals(
                signals=agent_signals, regime="normal", stock_symbol=symbol
            )

        result_dict = {
            "symbol": symbol,
            "current_price": current_price,
            "analysis_date": datetime.now().isoformat(),
            "features": features,
            "agent_signals": [s.to_dict() for s in agent_signals],
            "aggregated_signal": aggregated_signal.to_dict()
            if aggregated_signal
            else None,
            "data_points": len(df),
        }

        if mf_analysis:
            result_dict["mf_analysis"] = mf_analysis

        return result_dict

    async def run_backtest(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        logger.info(f"Running backtest: {symbols} from {start_date} to {end_date}")

        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        data: Dict[str, pd.DataFrame] = {}

        for symbol in symbols:
            df = await self.fetch_market_data(symbol, days=500)
            if df is not None and not df.empty:
                df = TechnicalFeatures.calculate_all(df)
                data[symbol] = df
                logger.info(f"Loaded {len(df)} days of data for {symbol}")

        if not data:
            return {"error": "Failed to fetch data for any symbol"}

        backtest_config = BacktestConfigExtended(
            initial_capital=initial_capital,
            commission_rate=self.config.backtest.commission,
            slippage_rate=self.config.backtest.slippage,
            position_sizing_method="risk_based",
            max_position_size=self.config.portfolio.max_position_size,
        )

        engine = BacktestEngine(config=backtest_config, aggregator=self.aggregator)

        result = engine.run_backtest(
            data=data,
            agents=self.agents,
            start_date=start_dt,
            end_date=end_dt,
            regime="sideways",
        )

        summary = engine.get_results_summary(result)

        return {
            "symbols": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "metrics": summary,
            "num_trades": len(result.trades),
            "equity_curve": result.equity_curve.to_dict()
            if not result.equity_curve.empty
            else {},
        }

    async def run_live(
        self, symbols: List[str], interval_seconds: int = 60
    ) -> Dict[str, Any]:
        logger.info(f"Starting live trading mode for: {symbols}")

        logger.warning("Live trading is a placeholder - not connected to real broker")

        analysis_results = {}

        for symbol in symbols:
            result = await self.analyze_stock(symbol)
            analysis_results[symbol] = result

        return {
            "mode": "live",
            "symbols": symbols,
            "analysis_results": analysis_results,
            "note": "Live trading placeholder - no actual orders will be placed",
        }

    def shutdown(self) -> None:
        if self.dispatcher:
            self.dispatcher.shutdown()
        logger.info("Quant Trading System shutdown complete")


def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Quant Agent Trader - Multi-agent quantitative trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s analyze --symbol AAPL
  %(prog)s analyze --symbol AAPL,GOOGL,MSFT
  %(prog)s analyze --symbol RELIANCE,TCS,HDFCBANK
  %(prog)s analyze --symbol NIFTY 50
  %(prog)s backtest --symbols AAPL,GOOGL --start 2023-01-01 --end 2024-01-01
  %(prog)s backtest --symbols RELIANCE,TCS --start 2023-01-01 --end 2024-01-01
  %(prog)s live --symbols AAPL,MSFT
  %(prog)s live --symbols RELIANCE,INFY
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze stock(s)")
    analyze_parser.add_argument(
        "--symbol",
        "-s",
        type=str,
        required=True,
        help="Stock symbol(s), comma-separated (supports US and Indian symbols: RELIANCE, TCS, HDFCBANK, NIFTY 50, etc.)",
    )
    analyze_parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days of historical data (default: 365)",
    )

    backtest_parser = subparsers.add_parser("backtest", help="Run backtest")
    backtest_parser.add_argument(
        "--symbols", type=str, required=True, help="Stock symbols, comma-separated"
    )
    backtest_parser.add_argument(
        "--start", type=str, required=True, help="Start date (YYYY-MM-DD)"
    )
    backtest_parser.add_argument(
        "--end", type=str, required=True, help="End date (YYYY-MM-DD)"
    )
    backtest_parser.add_argument(
        "--capital",
        type=float,
        default=100000.0,
        help="Initial capital (default: 100000)",
    )

    live_parser = subparsers.add_parser("live", help="Run live trading mode")
    live_parser.add_argument(
        "--symbols", type=str, required=True, help="Stock symbols, comma-separated"
    )
    live_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Update interval in seconds (default: 60)",
    )

    return parser


def print_analysis_results(results: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print(f"ANALYSIS RESULTS: {results.get('symbol', 'N/A')}")
    print("=" * 60)

    print(f"\nCurrent Price: Rs.{results.get('current_price', 0):.2f}")
    print(f"Data Points: {results.get('data_points', 0)}")
    print(f"Analysis Date: {results.get('analysis_date', 'N/A')}")

    mf_analysis = results.get("mf_analysis")
    if mf_analysis:
        print("\n" + "-" * 40)
        print("MUTUAL FUND HOLDINGS")
        print("-" * 40)

        mf_data = mf_analysis.get("mf", {})
        fii_data = mf_analysis.get("fii", {})
        analysis = mf_analysis.get("analysis", {})

        num_mfs = mf_data.get("num_mfs_holding", 0)
        mf_pct = mf_data.get("mf_holding_pct", 0.0)
        mf_change = mf_data.get("change_in_holding", 0.0)

        print(f"  MFs Holding: {num_mfs}")
        print(f"  MF Ownership: {mf_pct:.2f}%")
        print(f"  Change in Holdings: {'+' if mf_change >= 0 else ''}{mf_change:.2f}%")

        fii_pct = fii_data.get("fii_holding_pct", 0.0)
        fii_change = fii_data.get("fii_change", 0.0)
        print(f"  FII Ownership: {fii_pct:.2f}%")
        print(f"  FII Change: {'+' if fii_change >= 0 else ''}{fii_change:.2f}%")

        total_inst = mf_pct + fii_pct
        print(f"  Total Institutional: {total_inst:.2f}%")

        sentiment = analysis.get("sentiment", "N/A")
        smart_money = analysis.get("smart_money", "N/A")
        trend = analysis.get("trend", "N/A")

        print(f"\n  Sentiment: {sentiment}")
        print(f"  Smart Money: {smart_money}")
        print(f"  Trend: {trend}")

        top_holders = mf_data.get("top_mf_holders", [])
        if top_holders:
            print(f"\n  Top MF Holders:")
            for holder in top_holders[:5]:
                holder_name = holder.get("holder", "Unknown")[:25]
                holder_pct = holder.get("pct", 0)
                print(f"    - {holder_name:25s} {holder_pct:.2f}%")

        monthly_trend = mf_data.get("monthly_trend", [])
        if monthly_trend:
            print(f"\n  Monthly Trend (4 months):")
            for month_data in monthly_trend:
                month = month_data.get("month", "N/A")
                trend_pct = month_data.get("mf_holding_pct", 0)
                trend_mfs = month_data.get("num_mfs", 0)
                print(f"    {month}: {trend_pct:.2f}% ({trend_mfs} MFs)")

    aggregated = results.get("aggregated_signal")
    if aggregated:
        print("\n" + "-" * 40)
        print("AGGREGATED SIGNAL")
        print("-" * 40)
        # Debug: print all keys (removed for cleaner output)
        print(f"  Decision: {aggregated.get('decision', 'N/A')}")
        print(f"  Confidence: {aggregated.get('confidence', 0):.1f}%")
        print(f"  Final Score: {aggregated.get('final_score', 0):.3f}")
        print(f"  Regime: {aggregated.get('regime', 'N/A')}")

        supporting = aggregated.get("supporting_agents", [])
        conflicting = aggregated.get("conflicting_agents", [])

        if supporting:
            print(f"\n  Supporting Agents ({len(supporting)}):")
            for agent in supporting[:5]:
                print(f"    - {agent}")
            if len(supporting) > 5:
                print(f"    ... and {len(supporting) - 5} more")

        if conflicting:
            print(f"\n  Conflicting Agents ({len(conflicting)}):")
            for agent in conflicting[:5]:
                print(f"    - {agent}")
            if len(conflicting) > 5:
                print(f"    ... and {len(conflicting) - 5} more")

    agent_signals = results.get("agent_signals", [])
    if agent_signals:
        print("\n" + "-" * 40)
        print(f"INDIVIDUAL AGENT SIGNALS ({len(agent_signals)} agents)")
        print("-" * 40)

        for signal in agent_signals:
            signal_type = signal.get("signal", "N/A").upper()
            confidence = signal.get("confidence", 0)
            agent_name = signal.get("agent_name", "N/A")

            signal_emoji = {"BUY": "+", "SELL": "-", "HOLD": "="}.get(signal_type, "?")

            print(
                f"  {signal_emoji} {agent_name:20s} | {signal_type:5s} | Conf: {confidence:5.1f}%"
            )

    print("\n" + "=" * 60)


def print_backtest_results(results: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    print(f"\nSymbols: {', '.join(results.get('symbols', []))}")
    print(f"Period: {results.get('start_date')} to {results.get('end_date')}")
    print(f"Initial Capital: Rs.{results.get('initial_capital', 0):,.2f}")
    print(f"Total Trades: {results.get('num_trades', 0)}")

    metrics = results.get("metrics", {})

    if "Performance Summary" in metrics:
        print("\n" + "-" * 40)
        print("PERFORMANCE SUMMARY")
        print("-" * 40)

        for key, value in metrics["Performance Summary"].items():
            print(f"  {key}: {value}")

    if "Risk Metrics" in metrics:
        print("\n" + "-" * 40)
        print("RISK METRICS")
        print("-" * 40)

        for key, value in metrics["Risk Metrics"].items():
            print(f"  {key}: {value}")

    if "Trade Statistics" in metrics:
        print("\n" + "-" * 40)
        print("TRADE STATISTICS")
        print("-" * 40)

        for key, value in metrics["Trade Statistics"].items():
            print(f"  {key}: {value}")

    if "Capital" in metrics:
        print("\n" + "-" * 40)
        print("CAPITAL")
        print("-" * 40)

        for key, value in metrics["Capital"].items():
            print(f"  {key}: {value}")

    print("\n" + "=" * 60)


def print_live_results(results: Dict[str, Any]) -> None:
    print("\n" + "=" * 60)
    print("LIVE TRADING MODE")
    print("=" * 60)

    print(f"\nMode: {results.get('mode', 'N/A')}")
    print(f"Symbols: {', '.join(results.get('symbols', []))}")
    print(f"\nNote: {results.get('note', '')}")

    analysis_results = results.get("analysis_results", {})

    print("\n" + "-" * 40)
    print("ANALYSIS RESULTS")
    print("-" * 40)

    for symbol, analysis in analysis_results.items():
        print(f"\n{symbol}:")

        aggregated = analysis.get("aggregated_signal")
        if aggregated:
            decision = aggregated.get("decision", "N/A").upper()
            confidence = aggregated.get("confidence", 0)
            print(f"  Decision: {decision} (Confidence: {confidence:.1f}%)")

    print("\n" + "=" * 60)


async def main_async(args: argparse.Namespace) -> None:
    # Check for holdings directory before any computation
    from data.import_portfolio import check_holdings_exists, get_holdings_dir

    if not check_holdings_exists():
        holdings_dir = get_holdings_dir()
        print("=" * 60)
        print("ERROR: Holdings directory not found or empty!")
        print("=" * 60)
        print(f"\nRequired directory: {holdings_dir}")
        print("\nPlease export your holdings from your broker (Zerodha/Upstox)")
        print("and save as CSV file(s) in the above directory.")
        print("\nAlternatively, update HOLDINGS_DIR in .env file")
        print("\nAborting - no computation will be performed without holdings data.")
        print("=" * 60)
        sys.exit(1)

    # Import validation utilities
    from utils.validation import validate_stock_symbol, sanitize_symbol

    system = QuantTradingSystem()

    try:
        if args.command == "analyze":
            raw_symbols = [s.strip() for s in args.symbol.split(",")]

            # Validate and sanitize symbols
            symbols = []
            for symbol in raw_symbols:
                sanitized = sanitize_symbol(symbol)
                if validate_stock_symbol(sanitized):
                    symbols.append(sanitized)
                else:
                    logger.warning(f"Invalid symbol skipped: {symbol}")

            if not symbols:
                print("ERROR: No valid symbols provided")
                sys.exit(1)

            for symbol in symbols:
                results = await system.analyze_stock(symbol)
                print_analysis_results(results)

        elif args.command == "backtest":
            from utils.validation import validate_date_range, validate_capital

            # Validate date range
            date_valid, date_error = validate_date_range(args.start, args.end)
            if not date_valid:
                print(f"ERROR: {date_error}")
                sys.exit(1)

            # Validate capital
            capital_valid, capital_error = validate_capital(args.capital)
            if not capital_valid:
                print(f"ERROR: {capital_error}")
                sys.exit(1)

            symbols = [s.strip() for s in args.symbols.split(",")]

            results = await system.run_backtest(
                symbols=symbols,
                start_date=args.start,
                end_date=args.end,
                initial_capital=args.capital,
            )

            if "error" in results:
                print(f"Error: {results['error']}")
            else:
                print_backtest_results(results)

        elif args.command == "live":
            symbols = [s.strip() for s in args.symbols.split(",")]

            results = await system.run_live(
                symbols=symbols, interval_seconds=args.interval
            )

            print_live_results(results)

        else:
            print("Please specify a command: analyze, backtest, or live")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"Error during execution: {e}")
        print(f"\nError: {e}")
        sys.exit(1)

    finally:
        system.shutdown()


def main() -> None:
    parser = create_cli_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
