"""
Paper Trading - Simulate live trading without real capital.

Usage:
    paper = PaperTrader()
    
    # Simulate order
    result = paper.execute_order(
        symbol="TCS",
        direction="buy",
        quantity=100,
        price=3500
    )
    
    # Get portfolio state
    portfolio = paper.get_portfolio()
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class Order:
    """Represents a trading order."""
    order_id: str
    symbol: str
    direction: str  # buy, sell
    quantity: float
    price: float
    order_type: str = "market"  # market, limit
    status: str = "pending"  # pending, filled, cancelled
    timestamp: datetime = field(default_factory=datetime.now)
    fill_price: Optional[float] = None


@dataclass
class Position:
    """Represents a position."""
    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    side: str  # long, short


@dataclass
class Trade:
    """Represents a completed trade."""
    trade_id: str
    symbol: str
    direction: str
    quantity: float
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    holding_period: int  # minutes
    timestamp: datetime


class PaperTrader:
    """
    Paper trading simulator.
    
    Simulates:
    - Order execution
    - Slippage
    - Transaction costs
    - Position tracking
    - P&L calculation
    """
    
    def __init__(
        self,
        initial_capital: float = 100000,
        commission_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        slippage_type: str = "fixed"  # fixed, adaptive
    ):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.slippage_type = slippage_type
        
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.trades: List[Trade] = {}
        
        self.order_counter = 0
        self.trade_counter = 0
        
        self.pending_orders: Dict[str, Order] = {}
    
    def execute_order(
        self,
        symbol: str,
        direction: str,
        quantity: float,
        price: float,
        order_type: str = "market"
    ) -> Dict[str, Any]:
        """
        Execute a paper trade.
        
        Args:
            symbol: Stock symbol
            direction: buy or sell
            quantity: Number of shares
            price: Limit price (for market orders, this is the reference)
            order_type: market or limit
            
        Returns:
            Execution result
        """
        self.order_counter += 1
        order_id = f"ORDER_{self.order_counter:06d}"
        
        slippage = self._calculate_slippage(price, direction)
        
        if direction == "buy":
            fill_price = price * (1 + slippage)
        else:
            fill_price = price * (1 - slippage)
        
        commission = fill_price * quantity * self.commission_rate
        
        total_cost = fill_price * quantity + commission
        
        if direction == "buy":
            if total_cost > self.cash:
                return {
                    "status": "rejected",
                    "reason": "Insufficient funds",
                    "order_id": order_id
                }
            
            if symbol in self.positions:
                pos = self.positions[symbol]
                new_qty = pos.quantity + quantity
                new_avg = (
                    (pos.quantity * pos.avg_entry_price + quantity * fill_price) 
                    / new_qty
                )
                pos.quantity = new_qty
                pos.avg_entry_price = new_avg
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_entry_price=fill_price,
                    current_price=fill_price,
                    side="long"
                )
            
            self.cash -= total_cost
            
        else:  # sell
            if symbol not in self.positions:
                return {
                    "status": "rejected",
                    "reason": "No position to sell",
                    "order_id": order_id
                }
            
            pos = self.positions[symbol]
            
            if quantity > pos.quantity:
                quantity = pos.quantity
            
            pnl = (fill_price - pos.avg_entry_price) * quantity
            pnl_percent = (fill_price - pos.avg_entry_price) / pos.avg_entry_price
            
            pos.quantity -= quantity
            
            if pos.quantity <= 0:
                del self.positions[symbol]
            
            self.cash += fill_price * quantity - commission
            
            self.trade_counter += 1
            trade_id = f"TRADE_{self.trade_counter:06d}"
            
            self.trades[trade_id] = Trade(
                trade_id=trade_id,
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                entry_price=pos.avg_entry_price,
                exit_price=fill_price,
                pnl=pnl,
                pnl_percent=pnl_percent,
                holding_period=0,
                timestamp=datetime.now()
            )
        
        logger.info(
            f"Paper {'BUY' if direction == 'buy' else 'SELL'} {symbol}: "
            f"{quantity} @ {fill_price:.2f}"
        )
        
        return {
            "status": "filled",
            "order_id": order_id,
            "fill_price": fill_price,
            "quantity": quantity,
            "commission": commission,
            "slippage": abs(fill_price - price)
        }
    
    def _calculate_slippage(self, price: float, direction: str) -> float:
        """Calculate slippage."""
        if self.slippage_type == "fixed":
            return self.slippage_rate
        else:
            volatility_factor = 1.0
            
            return self.slippage_rate * volatility_factor
    
    def update_prices(self, prices: Dict[str, float]) -> None:
        """Update current prices for all positions."""
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
    
    def get_portfolio(self) -> Dict[str, Any]:
        """Get current portfolio state."""
        positions_value = sum(
            p.quantity * p.current_price 
            for p in self.positions.values()
        )
        
        total_value = self.cash + positions_value
        
        total_pnl = total_value - self.initial_capital
        total_pnl_percent = total_pnl / self.initial_capital
        
        unrealized_pnl = sum(
            (p.current_price - p.avg_entry_price) * p.quantity
            for p in self.positions.values()
        )
        
        return {
            "cash": self.cash,
            "positions_value": positions_value,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "total_pnl_percent": total_pnl_percent,
            "unrealized_pnl": unrealized_pnl,
            "positions": {
                symbol: {
                    "quantity": p.quantity,
                    "avg_entry": p.avg_entry_price,
                    "current": p.current_price,
                    "pnl": (p.current_price - p.avg_entry_price) * p.quantity,
                    "pnl_percent": (p.current_price - p.avg_entry_price) / p.avg_entry_price
                }
                for symbol, p in self.positions.items()
            },
            "num_positions": len(self.positions)
        }
    
    def get_trades(self) -> List[Dict]:
        """Get all completed trades."""
        return [
            {
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "direction": t.direction,
                "quantity": t.quantity,
                "entry": t.entry_price,
                "exit": t.exit_price,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "timestamp": t.timestamp.isoformat()
            }
            for t in self.trades.values()
        ]
    
    def reset(self) -> None:
        """Reset paper trader to initial state."""
        self.cash = self.initial_capital
        self.positions.clear()
        self.orders.clear()
        self.trades.clear()
        self.order_counter = 0
        self.trade_counter = 0
        logger.info("Paper trader reset")


class PaperPortfolioManager:
    """
    Paper portfolio with advanced features.
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.trader = PaperTrader(initial_capital)
        self.initial_capital = initial_capital
    
    def rebalance(self, target_weights: Dict[str, float], prices: Dict[str, float]) -> List[Dict]:
        """Rebalance portfolio to target weights."""
        self.trader.update_prices(prices)
        
        portfolio = self.trader.get_portfolio()
        current_value = portfolio["total_value"]
        
        orders = []
        
        for symbol, target_weight in target_weights.items():
            target_value = current_value * target_weight
            current_position = portfolio["positions"].get(symbol, {})
            current_value_pos = current_position.get("quantity", 0) * current_position.get("current", 0)
            
            diff_value = target_value - current_value_pos
            
            if abs(diff_value) < 100:
                continue
            
            price = prices.get(symbol, 0)
            if price <= 0:
                continue
            
            quantity = int(diff_value / price)
            
            if quantity > 0:
                result = self.trader.execute_order(
                    symbol=symbol,
                    direction="buy",
                    quantity=quantity,
                    price=price
                )
                orders.append(result)
            elif quantity < 0:
                result = self.trader.execute_order(
                    symbol=symbol,
                    direction="sell",
                    quantity=abs(quantity),
                    price=price
                )
                orders.append(result)
        
        return orders
    
    def get_performance(self) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        trades = self.trader.get_trades()
        
        if not trades:
            return {}
        
        pnls = [t["pnl"] for t in trades]
        
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p <= 0]
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(trades) if trades else 0,
            "total_pnl": sum(pnls),
            "avg_win": np.mean(winning_trades) if winning_trades else 0,
            "avg_loss": np.mean(losing_trades) if losing_trades else 0,
            "profit_factor": (
                abs(sum(winning_trades) / sum(losing_trades))
                if losing_trades and sum(losing_trades) != 0 else 0
            )
        }
