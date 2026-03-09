"""
Debugging Cheatsheet - Quick reference for debugging the quant trading system.

When encountering errors, use this systematic approach:

ATTRIBUTE ERROR
---------------
Usually indicates:
- enum missing from schema
- object property name wrong
- class not initialized

Example:
    AttributeError: QUANT

Solution:
    1. Check signals/signal_schema.py for enum definition
    2. Search for where enum is used: grep -r "QUANT" .
    3. Verify AgentCategory.QUANT exists


IMPORT ERROR / MODULE NOT FOUND
-------------------------------
Usually indicates:
- Missing __init__.py in directory
- Virtual environment not activated
- Wrong folder structure

Solution:
    1. Check directory has __init__.py
    2. Verify PYTHONPATH includes project root
    3. Check virtual environment is activated


KEY ERROR
---------
Usually indicates:
- Dictionary field not present
- Feature pipeline mismatch

Solution:
    1. Check dictionary keys with .keys()
    2. Add default value with .get(key, default)
    3. Verify feature names match


TYPE ERROR
----------
Usually indicates:
- Wrong data type passed
- None value not handled

Solution:
    1. Check parameter types in function signature
    2. Add None checks: if value is None: ...
    3. Use type hints for clarity


ASYNC BUGS
----------
Usually indicates:
- Missing await keyword
- Event loop conflict

Solution:
    1. Check all async functions have await
    2. Verify event loop is properly managed
    3. Use asyncio.gather() for parallel tasks


LAYER-BY-LAYER DEBUGGING
-------------------------
Use structured logging to identify failing layer:

    from utils.structured_logging import get_logger, LogLayer
    
    logger = get_logger(__name__, LogLayer.AGENT)
    logger.info("Running RSI agent")

Layer tags:
    [DATA] - Market data fetching
    [FEATURE] - Feature computation
    [AGENT] - Agent signal generation
    [AGGREGATOR] - Signal aggregation
    [META] - ML meta model
    [BACKTEST] - Backtest execution
    [PORTFOLIO] - Position sizing
    [EXECUTION] - Order execution


MINIMAL REPRODUCTION
--------------------
Instead of running whole system:

    # Test single component
    python -c "
    from signals.signal_schema import AgentCategory
    print(AgentCategory.QUANT)
    "

If that fails, bug is isolated to that component.


QUICK DEBUG COMMANDS
--------------------
# List all agents
python -c "from agents.agent_dispatcher import AgentDispatcher; d = AgentDispatcher(); print(d.list_agents())"

# Test single agent
python -c "
from agents.technical.rsi_agent import RSIAgent
agent = RSIAgent()
signal = agent.run({'price': 100, 'rsi': 30})
print(signal)
"

# Test aggregation
python -c "
from signals.signal_aggregator import SignalAggregator
from signals.signal_schema import AgentSignal
agg = SignalAggregator()
signals = [AgentSignal('test', 'technical', 'buy', 70, 0.7)]
result = agg.aggregate_signals(signals, 'bull', 'AAPL')
print(result.decision)
"


COMMON ISSUES AND FIXES
-----------------------
1. "QUANT not found in AgentCategory"
   -> Add QUANT = "quant" to AgentCategory enum in signal_schema.py

2. "AgentSignal missing required field"
   -> Check AgentSignal dataclass fields match agent output

3. "Model not trained"
   -> Call meta_model.train() before using aggregate_signals()

4. "Empty feature vector"
   -> Ensure signals list is not empty before calling feature_extractor
"""

import os

os.makedirs("data/training", exist_ok=True)
