"""
Execution Engine Tests

Tests for order execution functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from execution.execution_engine import ExecutionEngine
from execution.order_schema import OrderSchema, Order, OrderStatus, OrderSide, OrderType


class TestExecutionEngine:
    """Tests for ExecutionEngine class."""

    @pytest.fixture
    def engine(self):
        """Create execution engine instance."""
        return ExecutionEngine()

    def test_engine_initialization(self, engine):
        """Test execution engine initializes."""
        assert engine is not None

    def test_create_order(self, engine):
        """Test order creation."""
        order = engine.create_order(
            symbol="RELIANCE",
            side="buy",
            quantity=100,
            price=2950.0,
            order_type="limit",
        )

        assert order["symbol"] == "RELIANCE"
        assert order["quantity"] == 100
        assert order["side"] == "buy"

    def test_order_validation_valid(self, engine):
        """Test valid order validation."""
        order = Order(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            quantity=100,
            price=2950.0,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING,
        )

        is_valid, error = engine.validate_order(order)

        assert is_valid is True
        assert error is None

    def test_order_validation_zero_quantity(self, engine):
        """Test order with zero quantity."""
        order = Order(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            quantity=0,
            price=2950.0,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING,
        )

        is_valid, error = engine.validate_order(order)

        assert is_valid is False
        assert "quantity" in error.lower()

    def test_order_validation_negative_price(self, engine):
        """Test order with negative price."""
        order = Order(
            symbol="RELIANCE",
            side=OrderSide.BUY,
            quantity=100,
            price=-100.0,
            order_type=OrderType.LIMIT,
            status=OrderStatus.PENDING,
        )

        is_valid, error = engine.validate_order(order)

        assert is_valid is False

    def test_calculate_commission(self, engine):
        """Test commission calculation."""
        commission = engine.calculate_commission(
            price=2950.0, quantity=100, commission_rate=0.001
        )

        assert commission == 295.0  # 2950 * 100 * 0.001

    def test_calculate_commission_zero_rate(self, engine):
        """Test commission with zero rate."""
        commission = engine.calculate_commission(
            price=2950.0, quantity=100, commission_rate=0.0
        )

        assert commission == 0

    def test_calculate_slippage(self, engine):
        """Test slippage calculation."""
        slippage = engine.calculate_slippage(
            price=2950.0, quantity=100, slippage_pct=0.0005
        )

        assert slippage == 147.5  # 2950 * 100 * 0.0005

    def test_get_order_status(self, engine):
        """Test getting order status."""
        order_id = "test_order_1"

        status = engine.get_order_status(order_id)

        assert status is not None

    def test_cancel_order(self, engine):
        """Test order cancellation."""
        result = engine.cancel_order("test_order_1")

        assert isinstance(result, dict)

    def test_modify_order(self, engine):
        """Test order modification."""
        result = engine.modify_order(
            order_id="test_order_1", new_price=3000.0, new_quantity=150
        )

        assert isinstance(result, dict)


class TestOrderSchema:
    """Tests for OrderSchema."""

    def test_order_schema_creation(self):
        """Test creating an order with schema."""
        order = OrderSchema(
            symbol="RELIANCE",
            side="buy",
            quantity=100,
            price=2950.0,
            order_type="limit",
        )

        assert order.symbol == "RELIANCE"
        assert order.quantity == 100

    def test_order_to_dict(self):
        """Test order to dictionary conversion."""
        order = OrderSchema(
            symbol="RELIANCE",
            side="buy",
            quantity=100,
            price=2950.0,
            order_type="limit",
        )

        order_dict = order.to_dict()

        assert isinstance(order_dict, dict)
        assert "symbol" in order_dict

    def test_order_from_dict(self):
        """Test order creation from dictionary."""
        order_dict = {
            "symbol": "RELIANCE",
            "side": "buy",
            "quantity": 100,
            "price": 2950.0,
            "order_type": "limit",
        }

        order = OrderSchema.from_dict(order_dict)

        assert order.symbol == "RELIANCE"
        assert order.quantity == 100


class TestOrderSide:
    """Tests for OrderSide enum."""

    def test_order_side_values(self):
        """Test order side values."""
        assert OrderSide.BUY.value == "buy"
        assert OrderSide.SELL.value == "sell"


class TestOrderType:
    """Tests for OrderType enum."""

    def test_order_type_values(self):
        """Test order type values."""
        assert OrderType.LIMIT.value == "limit"
        assert OrderType.MARKET.value == "market"
        assert OrderType.STOP_LOSS.value == "stop_loss"


class TestExecutionEngineEdgeCases:
    """Edge case tests for execution engine."""

    def test_zero_price_order(self):
        """Test with zero price."""
        engine = ExecutionEngine()

        commission = engine.calculate_commission(0, 100, 0.001)

        assert commission == 0

    def test_large_quantity(self):
        """Test with large quantity."""
        engine = ExecutionEngine()

        commission = engine.calculate_commission(2950.0, 1000000, 0.001)

        assert commission > 0

    def test_empty_symbol(self):
        """Test with empty symbol."""
        engine = ExecutionEngine()

        order = engine.create_order(
            symbol="", side="buy", quantity=100, price=2950.0, order_type="limit"
        )

        assert order["symbol"] == ""


class TestExecutionEngineMocked:
    """Tests with mocked external calls."""

    @pytest.mark.asyncio
    async def test_execute_order_mock(self):
        """Test order execution with mock."""
        engine = ExecutionEngine()

        with patch.object(
            engine, "_execute_order_async", new_callable=AsyncMock
        ) as mock_exec:
            mock_exec.return_value = {
                "status": "filled",
                "filled_price": 2950.0,
                "filled_quantity": 100,
            }

            result = await engine.execute_order_async(
                symbol="RELIANCE", side="buy", quantity=100, price=2950.0
            )

            assert result["status"] == "filled"

    def test_simulate_execution(self):
        """Test simulated execution."""
        engine = ExecutionEngine()

        result = engine.simulate_execution(
            symbol="RELIANCE", side="buy", quantity=100, price=2950.0
        )

        assert "status" in result
        assert "filled_price" in result
