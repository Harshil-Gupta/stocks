"""
Training Dataset Generator - Integrates with backtest to generate ML datasets.

Extends the backtest engine to automatically:
1. Run agents
2. Generate feature rows
3. Compute future returns as labels
4. Save to feature store
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging

from signals.signal_schema import AgentSignal
from signals.feature_extractor import FeatureExtractor
from data.feature_store import FeatureStore

logger = logging.getLogger(__name__)


class TrainingDataGenerator:
    """
    Generates training data from backtest runs.
    
    Pipeline:
        1. Run agents for each date/symbol
        2. Extract features from agent outputs
        3. Compute future returns as labels
        4. Save to feature store
    
    Usage:
        generator = TrainingDataGenerator()
        generator.run(data, agents, start_date, end_date)
    """
    
    def __init__(
        self,
        feature_store: Optional[FeatureStore] = None,
        label_horizons: List[int] = [5, 10, 20],
        min_history: int = 50
    ):
        self.feature_store = feature_store or FeatureStore()
        self.feature_extractor = FeatureExtractor()
        self.label_horizons = label_horizons
        self.min_history = min_history
        self.training_rows: List[Dict] = []
    
    def generate(
        self,
        data: Dict[str, pd.DataFrame],
        agents: List[Any],
        start_date: datetime,
        end_date: datetime,
        symbols: Optional[List[str]] = None,
        progress: bool = True
    ) -> pd.DataFrame:
        """
        Generate training data from historical data.
        
        Args:
            data: Dict of symbol -> OHLCV DataFrame
            agents: List of agents to run
            start_date: Start date
            end_date: End date
            symbols: Optional list of symbols to process
            progress: Show progress
            
        Returns:
            DataFrame of training features and labels
        """
        symbols = symbols or list(data.keys())
        
        all_dates = self._get_common_dates(data, start_date, end_date, symbols)
        
        total = len(all_dates) * len(symbols)
        processed = 0
        
        logger.info(f"Generating training data: {len(all_dates)} days x {len(symbols)} symbols")
        
        for current_date in all_dates:
            for symbol in symbols:
                if current_date not in data[symbol].index:
                    continue
                
                historical_data = data[symbol].loc[:current_date]
                
                if len(historical_data) < self.min_history:
                    continue
                
                try:
                    signals = self._run_agents(agents, historical_data)
                    
                    if not signals:
                        continue
                    
                    market_features = self._extract_market_features(historical_data)
                    
                    future_returns = self._compute_future_returns(
                        data[symbol], 
                        current_date
                    )
                    
                    row = self._build_feature_row(
                        timestamp=current_date,
                        symbol=symbol,
                        signals=signals,
                        market_features=market_features,
                        future_returns=future_returns
                    )
                    
                    self.training_rows.append(row)
                    
                except Exception as e:
                    logger.debug(f"Skipping {symbol} on {current_date}: {e}")
                    continue
                
                processed += 1
                if progress and processed % 100 == 0:
                    logger.info(f"Progress: {processed}/{total} ({100*processed/total:.1f}%)")
        
        df = pd.DataFrame(self.training_rows)
        
        logger.info(f"Generated {len(df)} training samples")
        
        if not df.empty:
            self.feature_store.write_batch(self.training_rows)
        
        return df
    
    def _run_agents(
        self, 
        agents: List[Any], 
        data: pd.DataFrame
    ) -> List[AgentSignal]:
        """Run agents and return signals."""
        signals = []
        
        for agent in agents:
            try:
                features = self._prepare_agent_features(data)
                signal = agent.run(features, use_cache=False)
                signals.append(signal)
            except Exception as e:
                logger.debug(f"Agent {getattr(agent, 'agent_name', 'unknown')} failed: {e}")
                continue
        
        return signals
    
    def _prepare_agent_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Prepare features for agents."""
        recent = data.iloc[-1]
        
        features = {
            "price": float(recent['close']),
            "open": float(recent['open']),
            "high": float(recent['high']),
            "low": float(recent['low']),
            "volume": float(recent.get('volume', 0)),
        }
        
        if len(data) >= 20:
            features['sma_20'] = float(data['close'].iloc[-20:].mean())
        
        if len(data) >= 50:
            features['sma_50'] = float(data['close'].iloc[-50:].mean())
        
        if len(data) >= 14:
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features['rsi'] = float((100 - (100 / (1 + rs))).iloc[-1])
        
        if len(data) >= 26:
            ema_12 = data['close'].ewm(span=12, adjust=False).mean()
            ema_26 = data['close'].ewm(span=26, adjust=False).mean()
            features['macd'] = float((ema_12 - ema_26).iloc[-1])
            features['macd_signal'] = float(
                (ema_12 - ema_26).ewm(span=9, adjust=False).mean().iloc[-1]
            )
        
        if len(data) >= 20:
            features['volatility'] = float(
                data['close'].pct_change().rolling(window=20).std().iloc[-1]
            )
        
        if len(data) >= 20:
            features['momentum'] = float(
                data['close'].iloc[-1] / data['close'].iloc[-20] - 1
            )
        
        return features
    
    def _extract_market_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract market features from price data."""
        recent = data.iloc[-1]
        
        features = {
            "close": float(recent['close']),
            "open": float(recent['open']),
            "high": float(recent['high']),
            "low": float(recent['low']),
            "volume": float(recent.get('volume', 0)),
        }
        
        if len(data) >= 20:
            features['volatility'] = float(
                data['close'].pct_change().rolling(20).std().iloc[-1]
            )
            features['returns_5d'] = float(
                data['close'].pct_change(5).iloc[-1]
            )
            features['returns_20d'] = float(
                data['close'].pct_change(20).iloc[-1]
            )
        
        if len(data) >= 14:
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features['rsi'] = float((100 - (100 / (1 + rs))).iloc[-1])
        
        if len(data) >= 26:
            ema_12 = data['close'].ewm(span=12, adjust=False).mean()
            ema_26 = data['close'].ewm(span=26, adjust=False).mean()
            features['macd'] = float((ema_12 - ema_26).iloc[-1])
        
        for window in [20, 50, 200]:
            if len(data) >= window:
                features[f'sma_{window}'] = float(
                    data['close'].iloc[-window:].mean()
                )
        
        if len(data) >= 14:
            high_low = data['high'] - data['low']
            high_close = abs(data['high'] - data['close'].shift())
            low_close = abs(data['low'] - data['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            features['atr'] = float(true_range.rolling(14).mean().iloc[-1])
        
        return features
    
    def _compute_future_returns(
        self,
        data: pd.DataFrame,
        current_date: datetime
    ) -> Dict[str, float]:
        """Compute future returns for labeling."""
        if current_date not in data.index:
            return {f"future_return_{h}d": np.nan for h in self.label_horizons}
        
        current_idx = data.index.get_loc(current_date)
        current_price = data.iloc[current_idx]['close']
        
        returns = {}
        
        for horizon in self.label_horizons:
            if current_idx + horizon < len(data):
                future_price = data.iloc[current_idx + horizon]['close']
                ret = (future_price - current_price) / current_price
                returns[f"future_return_{horizon}d"] = ret
            else:
                returns[f"future_return_{horizon}d"] = np.nan
        
        return returns
    
    def _build_feature_row(
        self,
        timestamp: datetime,
        symbol: str,
        signals: List[AgentSignal],
        market_features: Dict[str, float],
        future_returns: Dict[str, float]
    ) -> Dict[str, Any]:
        """Build a complete feature row."""
        agent_features = self.feature_extractor.signals_to_features(signals)
        
        row = {
            "timestamp": timestamp,
            "symbol": symbol
        }
        
        for key, value in agent_features.items():
            if key not in ["date", "symbol"]:
                row[key] = value
        
        row.update(market_features)
        
        for horizon in self.label_horizons:
            label_key = f"future_return_{horizon}d"
            row[label_key] = future_returns.get(label_key, np.nan)
            row[f"target_binary_{horizon}d"] = 1 if future_returns.get(label_key, 0) > 0 else 0
        
        return row
    
    def _get_common_dates(
        self,
        data: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime,
        symbols: List[str]
    ) -> List[datetime]:
        """Get common trading dates across symbols."""
        date_sets = []
        
        for symbol in symbols:
            if symbol not in data or data[symbol].empty:
                continue
            
            symbol_dates = data[symbol].index[
                (data[symbol].index >= start_date) & 
                (data[symbol].index <= end_date)
            ]
            date_sets.append(set(symbol_dates))
        
        if not date_sets:
            return []
        
        common = set.intersection(*date_sets) if len(date_sets) > 1 else date_sets[0]
        
        return sorted(list(common))
    
    def get_dataset(self) -> pd.DataFrame:
        """Get generated training data."""
        return pd.DataFrame(self.training_rows)
    
    def clear(self) -> None:
        """Clear stored training data."""
        self.training_rows = []


class IncrementalTrainingGenerator:
    """
    Generates training data incrementally for ongoing backtests.
    
    Use this for real-time feature collection during live backtesting.
    """
    
    def __init__(self, feature_store: Optional[FeatureStore] = None):
        self.feature_store = feature_store or FeatureStore()
        self.feature_extractor = FeatureExtractor()
    
    def add_sample(
        self,
        timestamp: datetime,
        symbol: str,
        signals: List[AgentSignal],
        market_data: pd.DataFrame,
        horizon: int = 5
    ) -> Optional[Dict]:
        """
        Add a single training sample.
        
        Args:
            timestamp: Current timestamp
            symbol: Stock symbol
            signals: Agent signals
            market_data: Historical price data
            horizon: Forward days for label
            
        Returns:
            Feature row or None if insufficient data
        """
        if len(market_data) < horizon + 1:
            return None
        
        current_price = market_data.iloc[-1]['close']
        future_price = market_data.iloc[-horizon]['close']
        
        future_return = (future_price - current_price) / current_price
        
        agent_features = self.feature_extractor.signals_to_features(signals)
        
        row = {
            "timestamp": timestamp,
            "symbol": symbol,
            **agent_features,
            "close": current_price,
            "volume": market_data.iloc[-1].get('volume', 0),
            "future_return_5d": future_return,
            f"target_binary_{horizon}d": 1 if future_return > 0 else 0
        }
        
        self.feature_store.write_batch([row])
        
        return row
