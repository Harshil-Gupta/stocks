"""
Strategy Evaluator - Backtesting engine for trading strategies.

This module provides the StrategyEvaluator class that backtests trading strategies
and calculates performance metrics including returns, Sharpe ratio, drawdown, etc.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from backtesting a strategy."""
    strategy_name: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    avg_holding_period: float
    calmar_ratio: float
    sortino_ratio: float
    equity_curve: List[float]
    trade_log: List[Dict] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "avg_holding_period": self.avg_holding_period,
            "calmar_ratio": self.calmar_ratio,
            "sortino_ratio": self.sortino_ratio,
            "monthly_returns": self.monthly_returns
        }
    
    @property
    def fitness(self) -> float:
        """Calculate overall fitness score for evolution."""
        if self.total_trades < 5:
            return 0.0
        
        return (
            0.4 * max(0, self.sharpe_ratio / 3) +
            0.3 * (self.win_rate) +
            0.2 * max(0, 1 - abs(self.max_drawdown)) +
            0.1 * min(1, self.total_trades / 50)
        )


@dataclass
class Trade:
    """Represents a single trade."""
    entry_date: datetime
    entry_price: float
    exit_date: datetime
    exit_price: float
    position_size: float
    direction: str  # 'long' or 'short'
    pnl: float
    pnl_percent: float
    holding_bars: int


class StrategyEvaluator:
    """
    Backtesting engine for evaluating trading strategies.
    
    Supports:
    - Long and short positions
    - Multiple timeframes
    - Risk management (stop loss, take profit)
    - Transaction costs
    - Performance metrics calculation
    """
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
        risk_free_rate: float = 0.06
    ):
        """
        Initialize the strategy evaluator.
        
        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade (0.001 = 0.1%)
            slippage: Slippage rate (0.0005 = 0.05%)
            risk_free_rate: Annual risk-free rate for Sharpe calculation
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.risk_free_rate = risk_free_rate
        logger.info(f"StrategyEvaluator initialized: capital={initial_capital}, commission={commission}")
    
    def evaluate(
        self,
        strategy,
        data: pd.DataFrame,
        indicators: Optional[Dict[str, pd.Series]] = None
    ) -> BacktestResult:
        """
        Evaluate a strategy on historical data.
        
        Args:
            strategy: Strategy object with entry/exit conditions
            data: DataFrame with OHLCV data
            indicators: Optional pre-calculated indicators
            
        Returns:
            BacktestResult with performance metrics
        """
        df = data.copy()
        
        # Standardize column names to lowercase
        df.columns = [c.lower() for c in df.columns]
        
        if indicators:
            for name, series in indicators.items():
                df[name] = series
        
        trades = self._run_backtest(strategy, df)
        equity_curve = self._calculate_equity_curve(trades)
        
        return self._calculate_metrics(strategy.name, trades, equity_curve, df)
    
    def _run_backtest(
        self,
        strategy,
        df: pd.DataFrame
    ) -> List[Trade]:
        """Run the backtest and generate trades."""
        trades = []
        position = None
        entry_bar = 0
        
        params = strategy.parameters
        risk_per_trade = strategy.risk_per_trade
        
        for i in range(50, len(df)):
            current_date = df.index[i]
            current_price = df['close'].iloc[i]
            current_atr = df.get('atr', pd.Series([current_price * 0.02] * len(df))).iloc[i]
            
            if position is None:
                if self._check_entry(df.iloc[:i+1], strategy.entry_conditions, params):
                    position_size = self.initial_capital * risk_per_trade / (current_atr * 2)
                    position_size = min(position_size, self.initial_capital * strategy.max_position_size / current_price)
                    
                    position = {
                        'entry_date': current_date,
                        'entry_price': current_price * (1 + self.slippage),
                        'size': position_size,
                        'direction': 'long',
                        'entry_bar': i
                    }
                    
            else:
                should_exit = False
                exit_reason = ""
                
                exit_conds = strategy.exit_conditions
                
                if 'trailing_stop' in exit_conds:
                    stop_mult = exit_conds['trailing_stop'].get('value', 2.0)
                    highest = df['high'].iloc[position['entry_bar']:i+1].max()
                    stop_price = highest - (current_atr * stop_mult)
                    if current_price < stop_price:
                        should_exit = True
                        exit_reason = "trailing_stop"
                
                if 'stop_loss' in exit_conds and not should_exit:
                    stop_mult = exit_conds['stop_loss'].get('value', 2.0)
                    stop_price = position['entry_price'] - (current_atr * stop_mult)
                    if current_price < stop_price:
                        should_exit = True
                        exit_reason = "stop_loss"
                
                if 'profit_target' in exit_conds and not should_exit:
                    target_pct = exit_conds['profit_target'].get('value', 0.05)
                    target_price = position['entry_price'] * (1 + target_pct)
                    if current_price >= target_price:
                        should_exit = True
                        exit_reason = "profit_target"
                
                if 'time_exit' in exit_conds and not should_exit:
                    bars_held = i - position['entry_bar']
                    max_bars = exit_conds['time_exit'].get('value', 20)
                    if bars_held >= max_bars:
                        should_exit = True
                        exit_reason = "time_exit"
                
                if not should_exit:
                    should_exit = self._check_exit(df.iloc[:i+1], strategy.exit_conditions, params)
                    exit_reason = "condition"
                
                if should_exit:
                    exit_price = current_price * (1 - self.slippage)
                    
                    pnl = (exit_price - position['entry_price']) * position['size']
                    pnl_percent = (exit_price - position['entry_price']) / position['entry_price']
                    
                    trade = Trade(
                        entry_date=position['entry_date'],
                        entry_price=position['entry_price'],
                        exit_date=current_date,
                        exit_price=exit_price,
                        position_size=position['size'],
                        direction=position['direction'],
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        holding_bars=i - position['entry_bar']
                    )
                    trades.append(trade)
                    position = None
        
        return trades
    
    def _check_entry(
        self,
        df: pd.DataFrame,
        conditions: Dict,
        params: Dict
    ) -> bool:
        """Check if entry conditions are met."""
        if not conditions:
            return True
            
        last = df.iloc[-1]
        
        for name, cond in conditions.items():
            indicator = cond.get('indicator')
            operator = cond.get('operator', '>')
            value = cond.get('value', 0)
            
            if indicator == 'rsi':
                rsi_period = params.get('rsi_period', 14)
                if len(df) >= rsi_period:
                    rsi_val = self._calculate_rsi(df['close'], rsi_period).iloc[-1]
                    if not self._evaluate_condition(rsi_val, operator, value):
                        return False
            
            elif indicator == 'sma_20' or indicator == 'sma':
                sma_period = params.get('sma_period', 20)
                if len(df) >= sma_period:
                    sma_val = df['close'].rolling(sma_period).mean().iloc[-1]
                    if last['close'] <= sma_val:
                        return False
            
            elif indicator == 'macd':
                fast = params.get('macd_fast', 12)
                slow = params.get('macd_slow', 26)
                signal = params.get('macd_signal', 9)
                if len(df) >= slow:
                    ema_fast = df['close'].ewm(span=fast).mean()
                    ema_slow = df['close'].ewm(span=slow).mean()
                    macd = ema_fast - ema_slow
                    macd_signal = macd.ewm(span=signal).mean()
                    if not self._evaluate_condition(macd.iloc[-1], operator, value):
                        return False
            
            elif indicator == 'bb_lower':
                bb_period = params.get('bb_period', 20)
                bb_std = params.get('bb_std', 2.0)
                if len(df) >= bb_period:
                    sma = df['close'].rolling(bb_period).mean()
                    std = df['close'].rolling(bb_period).std()
                    bb_lower = sma - (std * bb_std)
                    if not self._evaluate_condition(last['close'], operator, bb_lower.iloc[-1]):
                        return False
            
            elif indicator == 'volume_ratio':
                if len(df) >= 20:
                    vol_ma = df['volume'].rolling(20).mean().iloc[-1]
                    ratio = last['volume'] / vol_ma if vol_ma > 0 else 1
                    if not self._evaluate_condition(ratio, operator, value):
                        return False
        
        return True
    
    def _check_exit(
        self,
        df: pd.DataFrame,
        conditions: Dict,
        params: Dict
    ) -> bool:
        """Check if exit conditions are met."""
        if not conditions:
            return False
            
        last = df.iloc[-1]
        
        for name, cond in conditions.items():
            if cond.get('type') in ['trailing_stop', 'stop_loss', 'profit_target', 'time_exit']:
                continue
                
            indicator = cond.get('indicator')
            operator = cond.get('operator', '>')
            value = cond.get('value', 0)
            
            if indicator == 'rsi':
                rsi_period = params.get('rsi_period', 14)
                if len(df) >= rsi_period:
                    rsi_val = self._calculate_rsi(df['close'], rsi_period).iloc[-1]
                    if self._evaluate_condition(rsi_val, operator, value):
                        return True
            
            elif indicator == 'sma_20':
                sma_period = params.get('sma_period', 20)
                if len(df) >= sma_period:
                    sma_val = df['close'].rolling(sma_period).mean().iloc[-1]
                    if self._evaluate_condition(last['close'], operator, sma_val):
                        return True
        
        return False
    
    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate a single condition."""
        ops = {
            '>': lambda v, t: v > t,
            '<': lambda v, t: v < t,
            '>=': lambda v, t: v >= t,
            '<=': lambda v, t: v <= t,
            '==': lambda v, t: abs(v - t) < 0.001
        }
        return ops.get(operator, lambda v, t: False)(value, threshold)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        
        # Avoid division by zero
        loss = loss.replace(0, 0.0001)
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_equity_curve(self, trades: List[Trade]) -> List[float]:
        """Calculate equity curve from trades."""
        equity = [self.initial_capital]
        for trade in trades:
            equity.append(equity[-1] + trade.pnl)
        return equity
    
    def _calculate_metrics(
        self,
        strategy_name: str,
        trades: List[Trade],
        equity_curve: List[float],
        df: pd.DataFrame
    ) -> BacktestResult:
        """Calculate performance metrics."""
        if not trades:
            return BacktestResult(
                strategy_name=strategy_name,
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win=0.0,
                avg_loss=0.0,
                avg_holding_period=0.0,
                calmar_ratio=0.0,
                sortino_ratio=0.0,
                equity_curve=equity_curve
            )
        
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in trades)
        total_return = total_pnl / self.initial_capital
        
        winning_pnl = sum(t.pnl for t in winning) if winning else 0
        losing_pnl = abs(sum(t.pnl for t in losing)) if losing else 1
        
        returns = [t.pnl_percent for t in trades]
        sharpe = self._calculate_sharpe(returns)
        sortino = self._calculate_sortino(returns)
        max_dd = self._calculate_max_drawdown(equity_curve)
        calmar = total_return / abs(max_dd) if max_dd != 0 else 0
        
        monthly = self._calculate_monthly_returns(trades, df)
        
        return BacktestResult(
            strategy_name=strategy_name,
            total_return=total_return,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            win_rate=len(winning) / len(trades) if trades else 0,
            profit_factor=winning_pnl / losing_pnl if losing_pnl > 0 else 0,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=sum(t.pnl for t in winning) / len(winning) if winning else 0,
            avg_loss=sum(t.pnl for t in losing) / len(losing) if losing else 0,
            avg_holding_period=sum(t.holding_bars for t in trades) / len(trades),
            calmar_ratio=calmar,
            sortino_ratio=sortino,
            equity_curve=equity_curve,
            trade_log=[{
                'entry': t.entry_date.isoformat(),
                'exit': t.exit_date.isoformat(),
                'pnl': t.pnl,
                'pnl_percent': t.pnl_percent
            } for t in trades],
            monthly_returns=monthly
        )
    
    def _calculate_sharpe(self, returns: List[float]) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        returns_arr = np.array(returns)
        mean_ret = np.mean(returns_arr)
        std_ret = np.std(returns_arr)
        if std_ret == 0:
            return 0.0
        return (mean_ret - self.risk_free_rate / 252) / std_ret * np.sqrt(252)
    
    def _calculate_sortino(self, returns: List[float]) -> float:
        """Calculate Sortino ratio."""
        if len(returns) < 2:
            return 0.0
        returns_arr = np.array(returns)
        mean_ret = np.mean(returns_arr)
        downside = returns_arr[returns_arr < 0]
        if len(downside) == 0:
            return 0.0
        downside_std = np.std(downside)
        if downside_std == 0:
            return 0.0
        return (mean_ret - self.risk_free_rate / 252) / downside_std * np.sqrt(252)
    
    def _calculate_max_drawdown(self, equity: List[float]) -> float:
        """Calculate maximum drawdown."""
        equity_arr = np.array(equity)
        peak = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - peak) / peak
        return abs(np.min(drawdown))
    
    def _calculate_monthly_returns(
        self,
        trades: List[Trade],
        df: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculate monthly returns."""
        monthly = {}
        if not trades:
            return monthly
            
        for trade in trades:
            month_key = trade.exit_date.strftime('%Y-%m')
            if month_key not in monthly:
                monthly[month_key] = 0.0
            monthly[month_key] += trade.pnl_percent
        
        return monthly
    
    def compare_strategies(
        self,
        results: List[BacktestResult]
    ) -> Dict[str, Any]:
        """Compare multiple strategy results."""
        if not results:
            return {}
        
        sorted_results = sorted(results, key=lambda x: x.fitness, reverse=True)
        
        return {
            'best_strategy': sorted_results[0].strategy_name,
            'best_fitness': sorted_results[0].fitness,
            'best_sharpe': sorted_results[0].sharpe_ratio,
            'best_return': sorted_results[0].total_return,
            'all_results': [r.to_dict() for r in sorted_results]
        }
