# Quant Agent Trader - Implementation Plan

## Phase 1: Critical Fixes (Blocking Issues)

### 1.1 Fix Broken Imports
**File:** `quant-agent-trader/signals/signal_aggregator.py`
- Line 11: Change `from quant_agent_trader.signals.signal_schema import` to `from signals.signal_schema import`
- Line 12: Change `from quant_agent_trader.config.settings import` to `from config.settings import`

### 1.2 Fix AgentCategory Enum
**File:** `quant-agent-trader/signals/signal_schema.py`
- Line 26: Change `RISK = "quant"` to `RISK = "risk"`

### 1.3 Fix ATR Data Flow
**File:** `quant-agent-trader/portfolio/portfolio_engine.py`
- The ATR value is expected from `signal.agent_signals[0].supporting_data.get("atr")` but agents don't populate it
- Need to ensure technical agents include ATR in their `supporting_data`

---

## Phase 2: Core Infrastructure

### 2.1 Create AgentDispatcher
**New File:** `quant-agent-trader/agents/agent_dispatcher.py`

Purpose: Central orchestrator to run multiple agents for a symbol and collect results

Required Classes:
- `AgentDispatcher` class that:
  - Maintains registry of available agents
  - Runs agents in parallel using ThreadPoolExecutor
  - Supports filtering by agent category
  - Returns aggregated results from all agents
  - Handles timeouts and graceful failures

Methods:
- `register_agent(agent: BaseAgent)` - Add agent to dispatcher
- `dispatch(symbol: str, features: Dict, categories: Optional[List]) -> List[AgentSignal]`
- `dispatch_parallel(symbol: str, features: Dict, categories: Optional[List]) -> List[AgentSignal]`
- `get_available_agents() -> Dict[str, List[str]]`

### 2.2 Create RegimeClassifier
**New File:** `quant-agent-trader/agents/regime_classifier.py`

Purpose: Automatically detect market regime (bull, bear, sideways, high_volatility)

Required Classes:
- `RegimeClassifier` class that analyzes:
  - Price trend (SMA 50/200 crossover)
  - Volatility (ATR or standard deviation)
  - Momentum (RSI, MACD)
  - Volume patterns

Methods:
- `classify(df: pd.DataFrame) -> MarketRegime`
- `classify_current(df: pd.DataFrame) -> str` - Returns regime string
- `get_volatility_regime(df: pd.DataFrame) -> str`
- `get_trend_regime(df: pd.DataFrame) -> str`

Output: MarketRegime dataclass with regime_type, volatility, trend_strength, liquidity_score, confidence

---

## Phase 3: Agent Categories

### 3.1 Fundamental Agents

**New File:** `quant-agent-trader/agents/fundamental/valuation_agent.py`
- Analyzes P/E, P/B, P/S, EV/EBITDA ratios
- Compares to industry averages
- Signal: buy (undervalued), sell (overvalued), hold

**New File:** `quant-agent-trader/agents/fundamental/earnings_agent.py`
- Analyzes EPS growth, revenue growth, beat/miss history
- Signal based on earnings momentum

**New File:** `quant-agent-trader/agents/fundamental/cashflow_agent.py`
- Analyzes free cash flow, operating cash flow
- FCF yield and growth

**New File:** `quant-agent-trader/agents/fundamental/growth_agent.py`
- Analyzes revenue growth, earnings growth, book value growth
- PEG ratio calculation

### 3.2 Sentiment Agents

**New File:** `quant-agent-trader/agents/sentiment/news_sentiment_agent.py`
- Analyzes news headline sentiment (mock for now)
- Returns sentiment score and confidence

**New File:** `quant-agent-trader/agents/sentiment/analyst_rating_agent.py`
- Analyzes analyst consensus and recent changes
- Buy/sell rating distribution

### 3.3 Risk Agents

**New File:** `quant-agent-trader/agents/risk/volatility_regime_agent.py`
- Classifies volatility as low/normal/high/extreme
- Adjusts confidence based on volatility regime

**New File:** `quant-agent-trader/agents/risk/tail_risk_agent.py`
- Analyzes historical drawdowns
- Estimates probability of large losses

---

## Phase 4: Execution Module

### 4.1 Create Execution Engine
**New File:** `quant-agent-trader/execution/execution_engine.py`

Purpose: Execute trades (paper trading for now)

Required Classes:
- `ExecutionEngine` class with:
  - Paper trading mode (default)
  - Order management (market, limit, stop)
  - Position tracking
  - Trade logging

Methods:
- `submit_order(order: Order) -> OrderResult`
- `cancel_order(order_id: str) -> bool`
- `get_positions() -> Dict[str, Position]`
- `get_pending_orders() -> List[Order]`

### 4.2 Order Schema
**New File:** `quant-agent-trader/execution/order_schema.py`

Dataclasses:
- `Order` - symbol, side, order_type, quantity, price, stop_price
- `OrderResult` - order_id, status, filled_price, filled_quantity, timestamp
- `Position` - symbol, quantity, avg_price, current_price, unrealized_pnl

---

## Phase 5: Technical Agent Fixes

### 5.1 Add ATR to Technical Agents
Update all technical agents to include ATR in supporting_data:
- `rsi_agent.py`
- `macd_agent.py`
- `momentum_agent.py`
- `trend_agent.py`
- `breakout_agent.py`
- `volume_agent.py`

---

## Summary of Files to Create/Modify

### New Files to Create:
1. `agents/agent_dispatcher.py` - Agent orchestration
2. `agents/regime_classifier.py` - Market regime detection
3. `agents/fundamental/__init__.py`
4. `agents/fundamental/valuation_agent.py`
5. `agents/fundamental/earnings_agent.py`
6. `agents/fundamental/cashflow_agent.py`
7. `agents/fundamental/growth_agent.py`
8. `agents/sentiment/__init__.py`
9. `agents/sentiment/news_sentiment_agent.py`
10. `agents/sentiment/analyst_rating_agent.py`
11. `agents/risk/__init__.py`
12. `agents/risk/volatility_regime_agent.py`
13. `agents/risk/tail_risk_agent.py`
14. `execution/__init__.py`
15. `execution/execution_engine.py`
16. `execution/order_schema.py`

### Files to Modify:
1. `signals/signal_aggregator.py` - Fix imports
2. `signals/signal_schema.py` - Fix AgentCategory enum
3. `portfolio/portfolio_engine.py` - Fix ATR data flow
4. Technical agents - Add ATR to supporting_data

---

## Implementation Order

1. First fix critical bugs (Phase 1)
2. Then create core infrastructure (Phase 2)
3. Then add fundamental agents (Phase 3.1)
4. Then add sentiment and risk agents (Phase 3.2-3.3)
5. Then create execution module (Phase 4)
6. Finally fix technical agents (Phase 5)
