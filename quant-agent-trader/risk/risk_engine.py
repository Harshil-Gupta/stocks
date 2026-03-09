"""
Risk Engine - Professional risk management for trading.

Usage:
    engine = RiskEngine()
    
    # Check before trade
    result = engine.check_trade(trade_request)
    
    # Get portfolio risk
    risk = engine.get_portfolio_risk(positions)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    approved: bool
    reasons: List[str]
    risk_level: str
    adjustments: Optional[Dict[str, Any]] = None


@dataclass
class Position:
    """Position information."""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    side: str  # long, short


class RiskEngine:
    """
    Professional risk management engine.
    
    Controls:
    - Max position size
    - Max portfolio drawdown
    - Sector exposure
    - Correlation limits
    - Daily loss limits
    """
    
    def __init__(
        self,
        max_position_size: float = 0.25,
        max_portfolio_risk: float = 0.20,
        max_sector_exposure: float = 0.40,
        max_daily_loss: float = 0.05,
        max_correlation: float = 0.70,
        enable_circuit_breakers: bool = True
    ):
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.max_sector_exposure = max_sector_exposure
        self.max_daily_loss = max_daily_loss
        self.max_correlation = max_correlation
        self.enable_circuit_breakers = enable_circuit_breakers
        
        self.daily_pnl = 0.0
        self.peak_equity = 0.0
        self.current_equity = 0.0
        
        self.circuit_breaker_triggered = False
    
    def check_trade(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        price: float,
        portfolio_value: float,
        positions: List[Position],
        sector: Optional[str] = None
    ) -> RiskCheckResult:
        """
        Check if trade passes risk controls.
        
        Args:
            symbol: Stock symbol
            direction: buy or sell
            quantity: Number of shares
            price: Price per share
            portfolio_value: Total portfolio value
            positions: Current positions
            sector: Optional sector for sector limits
            
        Returns:
            RiskCheckResult
        """
        reasons = []
        adjustments = {}
        
        trade_value = quantity * price
        trade_size = trade_value / portfolio_value
        
        if trade_size > self.max_position_size:
            adjusted_size = self.max_position_size * portfolio_value
            adjusted_qty = adjusted_size / price
            adjustments["quantity"] = adjusted_qty
            adjustments["size_reduced"] = True
            reasons.append(f"Position size reduced from {trade_size:.2%} to {self.max_position_size:.2%}")
        
        current_exposure = sum(
            p.quantity * p.current_price 
            for p in positions 
            if p.symbol == symbol
        ) / portfolio_value
        
        new_exposure = current_exposure + (trade_size if direction == "buy" else 0)
        
        if new_exposure > self.max_position_size:
            return RiskCheckResult(
                approved=False,
                reasons=["Exceeds max position size"],
                risk_level="high"
            )
        
        if sector:
            sector_exposure = sum(
                p.quantity * p.current_price
                for p in positions
                if getattr(p, "sector", None) == sector
            ) / portfolio_value
            
            if direction == "buy":
                new_sector_exposure = sector_exposure + trade_size
                if new_sector_exposure > self.max_sector_exposure:
                    reasons.append(f"Sector {sector} would exceed {self.max_sector_exposure:.0%} limit")
        
        if self.circuit_breaker_triggered:
            return RiskCheckResult(
                approved=False,
                reasons=["Circuit breaker triggered - trading halted"],
                risk_level="extreme"
            )
        
        if self.daily_pnl < -self.max_daily_loss * portfolio_value:
            self.circuit_breaker_triggered = True
            return RiskCheckResult(
                approved=False,
                reasons=["Daily loss limit exceeded - circuit breaker triggered"],
                risk_level="extreme"
            )
        
        risk_level = "low"
        if len(reasons) > 0:
            risk_level = "medium"
        if adjustments:
            risk_level = "medium"
        
        return RiskCheckResult(
            approved=True,
            reasons=reasons if reasons else ["Trade approved"],
            risk_level=risk_level,
            adjustments=adjustments if adjustments else None
        )
    
    def get_portfolio_risk(
        self,
        positions: List[Position],
        portfolio_value: float
    ) -> Dict[str, Any]:
        """Calculate current portfolio risk metrics."""
        if not positions:
            return {
                "total_exposure": 0,
                "long_exposure": 0,
                "short_exposure": 0,
                "net_exposure": 0,
                "cash_position": 1.0,
                "var_95": 0,
                "risk_level": "low"
            }
        
        total_value = sum(p.quantity * p.current_price for p in positions)
        long_value = sum(
            p.quantity * p.current_price 
            for p in positions 
            if p.side == "long"
        )
        short_value = sum(
            p.quantity * p.current_price 
            for p in positions 
            if p.side == "short"
        )
        
        total_exposure = total_value / portfolio_value
        long_exposure = long_value / portfolio_value
        short_exposure = short_value / portfolio_value
        net_exposure = (long_value - short_value) / portfolio_value
        cash_position = 1.0 - total_exposure
        
        var_95 = self._calculate_var(positions, portfolio_value)
        
        risk_level = "low"
        if total_exposure > 0.8:
            risk_level = "high"
        elif total_exposure > 0.6:
            risk_level = "medium"
        
        if abs(net_exposure) > 0.5:
            risk_level = "high"
        
        return {
            "total_exposure": total_exposure,
            "long_exposure": long_exposure,
            "short_exposure": short_exposure,
            "net_exposure": net_exposure,
            "cash_position": cash_position,
            "var_95": var_95,
            "risk_level": risk_level,
            "positions_count": len(positions)
        }
    
    def _calculate_var(
        self,
        positions: List[Position],
        portfolio_value: float,
        confidence: float = 0.95
    ) -> float:
        """Calculate Value at Risk."""
        if not positions:
            return 0.0
        
        daily_volatility = 0.02
        
        portfolio_beta = 1.0
        
        var = portfolio_value * daily_volatility * portfolio_beta * 2.33
        
        return var / portfolio_value
    
    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily P&L."""
        self.daily_pnl = pnl
    
    def update_equity(self, equity: float) -> None:
        """Update current equity and check drawdown."""
        self.current_equity = equity
        
        if self.peak_equity == 0:
            self.peak_equity = equity
            return
        
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        drawdown = (self.peak_equity - equity) / self.peak_equity
        
        if drawdown > 0.20:
            self.circuit_breaker_triggered = True
            logger.warning(f"Drawdown limit exceeded: {drawdown:.2%}")
    
    def reset_daily(self) -> None:
        """Reset daily counters."""
        self.daily_pnl = 0.0
    
    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (use with caution)."""
        self.circuit_breaker_triggered = False
        logger.info("Circuit breaker manually reset")


class PositionRiskManager:
    """
    Manage risk at position level.
    """
    
    def __init__(
        self,
        max_loss_per_trade: float = 0.02,
        use_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.02
    ):
        self.max_loss_per_trade = max_loss_per_trade
        self.use_trailing_stop = use_trailing_stop
        self.trailing_stop_pct = trailing_stop_pct
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        portfolio_value: float,
        position_value: float
    ) -> float:
        """Calculate stop loss price."""
        max_loss_value = portfolio_value * self.max_loss_per_trade
        max_loss_pct = max_loss_value / position_value if position_value > 0 else 0
        
        if direction == "long":
            stop_loss = entry_price * (1 - max_loss_pct)
            
            if self.use_trailing_stop:
                trailing = entry_price * (1 - self.trailing_stop_pct)
                stop_loss = max(stop_loss, trailing)
        else:
            stop_loss = entry_price * (1 + max_loss_pct)
            
            if self.use_trailing_stop:
                trailing = entry_price * (1 + self.trailing_stop_pct)
                stop_loss = min(stop_loss, trailing)
        
        return stop_loss
    
    def calculate_take_profit(
        self,
        entry_price: float,
        direction: str,
        risk_reward_ratio: float = 2.0
    ) -> float:
        """Calculate take profit level."""
        max_loss_pct = self.max_loss_per_trade
        
        if direction == "long":
            return entry_price * (1 + max_loss_pct * risk_reward_ratio)
        else:
            return entry_price * (1 - max_loss_pct * risk_reward_ratio)


class CorrelationRiskManager:
    """
    Manage correlation risk across positions.
    """
    
    def __init__(self, max_correlation: float = 0.70):
        self.max_correlation = max_correlation
        self.returns_history: Dict[str, pd.Series] = {}
    
    def add_returns(self, symbol: str, returns: pd.Series) -> None:
        """Add return series for correlation calculation."""
        self.returns_history[symbol] = returns
    
    def check_correlation(
        self,
        new_symbol: str,
        new_returns: pd.Series,
        existing_positions: List[str]
    ) -> Dict[str, Any]:
        """Check correlation of new position with existing."""
        if not existing_positions or new_symbol not in self.returns_history:
            return {"approved": True, "correlations": {}}
        
        correlations = {}
        
        for symbol in existing_positions:
            if symbol in self.returns_history:
                corr = self.returns_history[symbol].corr(new_returns)
                correlations[symbol] = corr
        
        max_corr = max(abs(c) for c in correlations.values()) if correlations else 0
        
        if max_corr > self.max_correlation:
            return {
                "approved": False,
                "reason": f"Max correlation {max_corr:.2f} exceeds limit {self.max_correlation}",
                "correlations": correlations
            }
        
        return {
            "approved": True,
            "max_correlation": max_corr,
            "correlations": correlations
        }


def calculate_position_size_kelly(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    portfolio_value: float,
    fraction: float = 0.25
) -> float:
    """Calculate position size using Kelly Criterion."""
    if win_rate <= 0 or avg_win <= 0 or avg_loss <= 0:
        return 0.1 * portfolio_value
    
    b = avg_win / avg_loss
    kelly = (win_rate * b - (1 - win_rate)) / b
    
    kelly = max(0, kelly * fraction)
    
    return kelly * portfolio_value


def calculate_sharpe_contribution(
    position_return: float,
    position_volatility: float,
    risk_free_rate: float = 0.02
) -> float:
    """Calculate Sharpe ratio contribution."""
    if position_volatility == 0:
        return 0
    
    return (position_return - risk_free_rate) / position_volatility
