"""
Portfolio Decision Engine - Position sizing and portfolio management.

This module provides the core PortfolioEngine class for generating portfolio
decisions from aggregated signals, managing position sizes, stop-loss/take-profit
levels, and portfolio rebalancing.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

from signals.signal_schema import AggregatedSignal, PortfolioDecision, TradeResult
from config.settings import PortfolioConfig, SignalConfig, REGIME_WEIGHTS


logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Position:
    """Represents a single position in the portfolio."""
    stock_symbol: str
    entry_price: float
    current_price: float
    position_size: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_date: datetime = field(default_factory=datetime.now)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


@dataclass
class Portfolio:
    """Represents the overall portfolio state."""
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    total_value: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0


class PortfolioEngine:
    """
    Portfolio Decision Engine for generating trading decisions from aggregated signals.
    
    This engine handles position sizing, risk management, stop-loss/take-profit
    calculations, and portfolio rebalancing across multiple stocks.
    """
    
    def __init__(
        self,
        config: Optional[PortfolioConfig] = None,
        signal_config: Optional[SignalConfig] = None
    ):
        """
        Initialize the PortfolioEngine.
        
        Args:
            config: Portfolio configuration. Uses default if not provided.
            signal_config: Signal configuration for confidence threshold.
        """
        self.config = config or PortfolioConfig()
        self.signal_config = signal_config or SignalConfig()
        self.min_confidence_threshold = self.signal_config.min_confidence_threshold
        self.portfolio = Portfolio(cash=100000.0)
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[TradeResult] = []
        
        self._risk_reward_ratios = {
            "low": 3.0,
            "medium": 2.0,
            "high": 1.5
        }
        
        self._stop_loss_multipliers = {
            "bull": 2.0,
            "bear": 1.5,
            "sideways": 1.5,
            "high_volatility": 2.5
        }
    
    def evaluate_decision(
        self,
        signal: AggregatedSignal,
        current_prices: Dict[str, float]
    ) -> PortfolioDecision:
        """
        Generate a PortfolioDecision from an AggregatedSignal.
        
        Args:
            signal: The aggregated signal from multiple agents.
            current_prices: Dictionary of current prices for relevant stocks.
            
        Returns:
            PortfolioDecision with position sizing and risk management levels.
        """
        stock_symbol = signal.stock_symbol
        current_price = current_prices.get(stock_symbol, 0.0)
        
        if current_price <= 0:
            logger.warning(f"Invalid price for {stock_symbol}, skipping decision")
            return PortfolioDecision(
                stock_symbol=stock_symbol,
                decision="hold",
                position_size=0.0,
                confidence=0.0,
                risk_level="low",
                reasoning="Invalid price data"
            )
        
        decision = signal.decision
        confidence = signal.confidence
        regime = signal.regime
        
        if decision == "hold" or confidence < self.min_confidence_threshold * 100:
            return PortfolioDecision(
                stock_symbol=stock_symbol,
                decision="hold",
                position_size=0.0,
                confidence=confidence,
                risk_level="low",
                reasoning=f"Low confidence ({confidence}) or hold signal"
            )
        
        risk_level = self._determine_risk_level(confidence, regime)
        
        portfolio_value = self._calculate_portfolio_value(current_prices)
        position_size = self.calculate_position_size(
            signal=signal,
            portfolio_value=portfolio_value,
            risk_level=risk_level
        )
        
        atr = signal.agent_signals[0].supporting_data.get("atr", 0.0) if signal.agent_signals else 0.0
        stop_loss = self.calculate_stop_loss(current_price, atr, regime)
        take_profit = self.calculate_take_profit(current_price, self._risk_reward_ratios[risk_level])
        
        reasoning = self._build_reasoning(signal, position_size, risk_level, stop_loss, take_profit)
        
        return PortfolioDecision(
            stock_symbol=stock_symbol,
            decision=decision,
            position_size=position_size,
            confidence=confidence,
            risk_level=risk_level,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=reasoning
        )
    
    def calculate_position_size(
        self,
        signal: AggregatedSignal,
        portfolio_value: float,
        risk_level: str
    ) -> float:
        """
        Calculate position size based on signal confidence and risk level.
        
        Args:
            signal: The aggregated signal with confidence score.
            portfolio_value: Total portfolio value.
            risk_level: Risk level (low, medium, high).
            
        Returns:
            Position size as a fraction of portfolio (0-1).
        """
        confidence_factor = signal.confidence / 100.0
        
        risk_multipliers = {
            "low": 1.0,
            "medium": 0.75,
            "high": 0.5
        }
        
        base_size = self.config.default_position_size
        confidence_adjustment = confidence_factor * self.config.default_position_size
        
        size = min(
            confidence_adjustment * risk_multipliers.get(risk_level, 0.5),
            self.config.max_position_size
        )
        
        if len(self.positions) >= self.config.max_portfolio_stocks:
            size = min(size, self.config.default_position_size)
        
        return max(size, 0.0)
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        atr: float,
        regime: str
    ) -> Optional[float]:
        """
        Calculate stop-loss price based on ATR and market regime.
        
        Args:
            entry_price: Entry price for the position.
            atr: Average True Range value.
            regime: Current market regime.
            
        Returns:
            Stop-loss price, or None if ATR is not available.
        """
        if atr <= 0:
            atr = entry_price * 0.02
        
        multiplier = self._stop_loss_multipliers.get(regime, 2.0)
        
        stop_loss = entry_price - (atr * multiplier)
        
        return round(stop_loss, 2)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        risk_reward_ratio: float
    ) -> Optional[float]:
        """
        Calculate take-profit price based on risk-reward ratio.
        
        Args:
            entry_price: Entry price for the position.
            risk_reward_ratio: Target risk-reward ratio.
            
        Returns:
            Take-profit price.
        """
        stop_distance = entry_price * 0.02
        
        take_profit = entry_price + (stop_distance * risk_reward_ratio)
        
        return round(take_profit, 2)
    
    def rebalance_portfolio(
        self,
        positions: Dict[str, Position],
        target_allocation: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> List[PortfolioDecision]:
        """
        Rebalance portfolio to match target allocation.
        
        Args:
            positions: Current positions.
            target_allocation: Target allocation per stock (0-1).
            current_prices: Current prices for all stocks.
            
        Returns:
            List of rebalancing decisions.
        """
        decisions = []
        
        total_value = sum(
            pos.position_size * current_prices.get(symbol, pos.current_price)
            for symbol, pos in positions.items()
        )
        
        for symbol, target_pct in target_allocation.items():
            current_position = positions.get(symbol)
            current_price = current_prices.get(symbol, 0.0)
            
            if current_price <= 0:
                continue
            
            current_value = 0.0
            if current_position:
                current_value = current_position.position_size * current_price
            
            target_value = total_value * target_pct
            diff_value = target_value - current_value
            
            if abs(diff_value) / total_value < self.config.rebalance_threshold:
                continue
            
            if diff_value > 0:
                decision = "buy"
                position_size = diff_value / current_price
            else:
                decision = "sell"
                position_size = abs(diff_value) / current_price
            
            position_size = min(position_size, self.config.max_position_size)
            
            decisions.append(PortfolioDecision(
                stock_symbol=symbol,
                decision=decision,
                position_size=position_size,
                confidence=75.0,
                risk_level="medium",
                reasoning=f"Rebalancing: current {current_value/total_value:.2%} -> target {target_pct:.2%}"
            ))
        
        return decisions
    
    def get_portfolio_summary(self) -> Dict:
        """
        Get current portfolio summary.
        
        Returns:
            Dictionary containing portfolio metrics and positions.
        """
        positions_list = []
        total_unrealized = 0.0
        total_realized = 0.0
        
        for symbol, position in self.positions.items():
            positions_list.append({
                "symbol": symbol,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "position_size": position.position_size,
                "unrealized_pnl": position.unrealized_pnl,
                "realized_pnl": position.realized_pnl,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit
            })
            total_unrealized += position.unrealized_pnl
            total_realized += position.realized_pnl
        
        total_value = self.portfolio.cash + total_unrealized
        
        return {
            "total_value": total_value,
            "cash": self.portfolio.cash,
            "positions": positions_list,
            "num_positions": len(self.positions),
            "unrealized_pnl": total_unrealized,
            "realized_pnl": total_realized,
            "total_pnl": total_unrealized + total_realized
        }
    
    def update_position(
        self,
        symbol: str,
        current_price: float,
        update_pnl: bool = True
    ) -> None:
        """
        Update an existing position with current price.
        
        Args:
            symbol: Stock symbol.
            current_price: Current market price.
            update_pnl: Whether to update P&L calculations.
        """
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        position.current_price = current_price
        
        if update_pnl:
            position.unrealized_pnl = (
                (current_price - position.entry_price) * position.position_size
            )
    
    def close_position(
        self,
        symbol: str,
        exit_price: float
    ) -> Optional[TradeResult]:
        """
        Close a position and record the trade result.
        
        Args:
            symbol: Stock symbol.
            exit_price: Exit price.
            
        Returns:
            TradeResult if position existed, None otherwise.
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        pnl = (exit_price - position.entry_price) * position.position_size
        pnl_percent = ((exit_price / position.entry_price) - 1) * 100
        
        holding_period = (datetime.now() - position.entry_date).days
        
        trade_result = TradeResult(
            stock_symbol=symbol,
            entry_price=position.entry_price,
            exit_price=exit_price,
            position_size=position.position_size,
            pnl=pnl,
            pnl_percent=pnl_percent,
            holding_period=holding_period,
            decision="closed"
        )
        
        self.trade_history.append(trade_result)
        
        position.realized_pnl += pnl
        del self.positions[symbol]
        
        return trade_result
    
    def open_position(
        self,
        symbol: str,
        decision: PortfolioDecision,
        current_price: float
    ) -> Position:
        """
        Open a new position based on a portfolio decision.
        
        Args:
            symbol: Stock symbol.
            decision: Portfolio decision with position size and levels.
            current_price: Current market price.
            
        Returns:
            The opened position.
        """
        position_value = self.portfolio.cash * decision.position_size
        position_size = position_value / current_price
        
        position = Position(
            stock_symbol=symbol,
            entry_price=current_price,
            current_price=current_price,
            position_size=position_size,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit
        )
        
        self.positions[symbol] = position
        
        return position
    
    def _calculate_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value including open positions."""
        positions_value = sum(
            pos.position_size * current_prices.get(symbol, pos.current_price)
            for symbol, pos in self.positions.items()
        )
        return self.portfolio.cash + positions_value
    
    def _determine_risk_level(self, confidence: float, regime: str) -> str:
        """Determine risk level based on confidence and regime."""
        if confidence >= 75:
            if regime in ["bull", "sideways"]:
                return "low"
            return "medium"
        elif confidence >= 50:
            return "medium"
        else:
            return "high"
    
    def _build_reasoning(
        self,
        signal: AggregatedSignal,
        position_size: float,
        risk_level: str,
        stop_loss: Optional[float],
        take_profit: Optional[float]
    ) -> str:
        """Build reasoning string for the decision."""
        reasoning_parts = [
            f"Signal confidence: {signal.confidence:.1f}%",
            f"Regime: {signal.regime}",
            f"Position size: {position_size:.2%}",
            f"Risk level: {risk_level}"
        ]
        
        if stop_loss:
            reasoning_parts.append(f"Stop-loss: ₹{stop_loss:.2f}")
        if take_profit:
            reasoning_parts.append(f"Take-profit: ₹{take_profit:.2f}")
        
        return "; ".join(reasoning_parts)

