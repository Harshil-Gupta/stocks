from typing import Dict, List, Optional
from datetime import datetime
import logging
from dataclasses import dataclass, field

from execution.order_schema import Order, OrderResult, OrderStatus, Position
from signals.signal_schema import PortfolioDecision

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Paper trading execution engine.
    Simulates order execution without real money.
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
    
    def submit_market_order(self, symbol: str, side: str, quantity: float) -> OrderResult:
        """Submit a market order (simulated)."""
        order = Order(
            symbol=symbol,
            side=side,
            order_type="market",
            quantity=quantity
        )
        self.orders[order.order_id] = order
        
        filled_price = 100.0
        
        return self._fill_order(order, filled_price, quantity)
    
    def submit_limit_order(self, symbol: str, side: str, quantity: float, limit_price: float) -> OrderResult:
        """Submit a limit order."""
        order = Order(
            symbol=symbol,
            side=side,
            order_type="limit",
            quantity=quantity,
            price=limit_price
        )
        self.orders[order.order_id] = order
        return OrderResult(
            success=True,
            order_id=order.order_id,
            status=OrderStatus.PENDING.value,
            message=f"Limit order placed at {limit_price}"
        )
    
    def _fill_order(self, order: Order, filled_price: float, filled_quantity: float) -> OrderResult:
        """Fill an order."""
        order.status = OrderStatus.FILLED.value
        order.filled_price = filled_price
        order.filled_quantity = filled_quantity
        order.filled_at = datetime.now()
        
        self._update_position(order, filled_price, filled_quantity)
        
        return OrderResult(
            success=True,
            order_id=order.order_id,
            status=OrderStatus.FILLED.value,
            filled_price=filled_price,
            filled_quantity=filled_quantity
        )
    
    def _update_position(self, order: Order, price: float, quantity: float):
        """Update position after trade."""
        if order.side == "buy":
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_cost = pos.avg_price * pos.quantity + price * quantity
                pos.quantity += quantity
                pos.avg_price = total_cost / pos.quantity
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=quantity,
                    avg_price=price,
                    entry_date=datetime.now()
                )
            self.cash -= price * quantity
        else:
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                realized = (price - pos.avg_price) * quantity
                pos.realized_pnl += realized
                pos.quantity -= quantity
                if pos.quantity <= 0:
                    del self.positions[order.symbol]
            self.cash += price * quantity
    
    def get_positions(self) -> Dict[str, Position]:
        return self.positions
    
    def get_pending_orders(self) -> List[Order]:
        return [o for o in self.orders.values() if o.status == OrderStatus.PENDING.value]
    
    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED.value
            return True
        return False
    
    def get_account_summary(self) -> Dict:
        positions_value = sum(p.quantity * p.current_price for p in self.positions.values())
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        return {
            "cash": self.cash,
            "positions_value": positions_value,
            "unrealized_pnl": unrealized,
            "total_value": self.cash + positions_value,
            "num_positions": len(self.positions)
        }
    
    def execute_decision(self, decision: PortfolioDecision, current_price: float) -> OrderResult:
        """Execute a PortfolioDecision."""
        if decision.decision == "hold":
            return OrderResult(success=True, order_id="", status="hold", message="No action needed")
        
        position_value = self.cash * decision.position_size
        quantity = position_value / current_price
        
        if decision.decision == "buy":
            return self.submit_market_order(decision.stock_symbol, "buy", quantity)
        else:
            return self.submit_market_order(decision.stock_symbol, "sell", quantity)
