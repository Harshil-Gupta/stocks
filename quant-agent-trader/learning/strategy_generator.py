"""
Strategy Generator - Generates trading strategies using templates and parameters.

This module provides the StrategyGenerator class that creates diverse trading
strategies by combining technical indicators, entry/exit rules, and parameters.
"""

import random
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy

logger = logging.getLogger(__name__)


@dataclass
class Strategy:
    """Represents a trading strategy with parameters."""
    name: str
    strategy_type: str  # momentum, mean_reversion, breakout, trend_following
    entry_conditions: Dict[str, Any]
    exit_conditions: Dict[str, Any]
    parameters: Dict[str, Any]
    indicators: List[str]
    timeframes: List[str]
    risk_per_trade: float = 0.02
    max_position_size: float = 0.1
    created_at: datetime = field(default_factory=datetime.now)
    generation: int = 0
    fitness: float = 0.0
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "strategy_type": self.strategy_type,
            "entry_conditions": self.entry_conditions,
            "exit_conditions": self.exit_conditions,
            "parameters": self.parameters,
            "indicators": self.indicators,
            "timeframes": self.timeframes,
            "risk_per_trade": self.risk_per_trade,
            "max_position_size": self.max_position_size,
            "created_at": self.created_at.isoformat(),
            "generation": self.generation,
            "fitness": self.fitness,
            "parent_id": self.parent_id
        }
    
    def mutate(self, mutation_rate: float = 0.1) -> 'Strategy':
        """Create a mutated copy of this strategy."""
        mutated = deepcopy(self)
        mutated.name = f"{self.name}_m{datetime.now().strftime('%H%M%S')}"
        mutated.generation = self.generation + 1
        mutated.parent_id = self.name
        
        if random.random() < mutation_rate:
            mutated._mutate_parameters()
        if random.random() < mutation_rate:
            mutated._mutate_conditions()
        if random.random() < mutation_rate * 0.5:
            mutated._mutate_indicators()
            
        return mutated
    
    def _mutate_parameters(self):
        """Mutate strategy parameters."""
        for key, value in self.parameters.items():
            if isinstance(value, (int, float)):
                change = random.uniform(-0.2, 0.2) * value
                self.parameters[key] = max(0.001, value + change)
    
    def _mutate_conditions(self):
        """Mutate entry/exit conditions."""
        if random.random() < 0.3:
            operator = random.choice(['>', '<', '>=', '<='])
            threshold = random.uniform(0.1, 0.9)
            condition = random.choice(list(self.entry_conditions.keys()))
            self.entry_conditions[condition] = {"operator": operator, "value": threshold}
    
    def _mutate_indicators(self):
        """Mutate indicator list."""
        all_indicators = [
            'rsi', 'macd', 'sma_20', 'sma_50', 'sma_200', 'ema_12', 'ema_26',
            'bb_upper', 'bb_lower', 'bb_width', 'atr', 'adx', 'cci', 'stoch',
            'momentum', 'roc', 'williams_r', 'obv', 'mfi', 'volume_sma'
        ]
        if random.random() < 0.5 and len(self.indicators) < 5:
            new_ind = random.choice([i for i in all_indicators if i not in self.indicators])
            self.indicators.append(new_ind)
        elif len(self.indicators) > 1:
            self.indicators.pop(random.randint(0, len(self.indicators) - 1))


class StrategyGenerator:
    """
    Generates diverse trading strategies using templates and random parameters.
    
    Supports multiple strategy types:
    - momentum: Strategies based on trend momentum
    - mean_reversion: Strategies based on price returning to mean
    - breakout: Strategies based on price breaking levels
    - trend_following: Strategies that follow established trends
    """
    
    STRATEGY_TEMPLATES = {
        "momentum": {
            "entry_conditions": {
                "rsi_oversold": {"indicator": "rsi", "operator": "<", "value": 30},
                "price_above_sma": {"indicator": "sma_20", "operator": ">", "value": 0},
                "macd_bullish": {"indicator": "macd", "operator": ">", "value": 0}
            },
            "exit_conditions": {
                "rsi_overbought": {"indicator": "rsi", "operator": ">", "value": 70},
                "trailing_stop": {"type": "atr_multiplier", "value": 2.0}
            },
            "default_parameters": {
                "rsi_period": 14,
                "sma_period": 20,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9
            }
        },
        "mean_reversion": {
            "entry_conditions": {
                "bb_lower": {"indicator": "bb_lower", "operator": ">", "value": 0},
                "rsi_oversold": {"indicator": "rsi", "operator": "<", "value": 25},
                "low_volatility": {"indicator": "atr_percent", "operator": "<", "value": 0.03}
            },
            "exit_conditions": {
                "bb_middle": {"indicator": "bb_middle", "operator": ">", "value": 0},
                "rsi_neutral": {"indicator": "rsi", "operator": ">", "value": 50},
                "profit_target": {"type": "percent", "value": 0.05}
            },
            "default_parameters": {
                "bb_period": 20,
                "bb_std": 2.0,
                "rsi_period": 10,
                "atr_period": 14
            }
        },
        "breakout": {
            "entry_conditions": {
                "price_breakout": {"indicator": "close", "operator": ">", "value": 0},
                "volume_surge": {"indicator": "volume_ratio", "operator": ">", "value": 1.5},
                "atr_expansion": {"indicator": "atr_percent", "operator": ">", "value": 0.02}
            },
            "exit_conditions": {
                "breakout_failed": {"indicator": "close", "operator": "<", "value": 0},
                "trailing_stop": {"type": "atr_multiplier", "value": 3.0},
                "time_exit": {"type": "bars", "value": 20}
            },
            "default_parameters": {
                "lookback_period": 20,
                "volume_ma_period": 20,
                "atr_period": 14
            }
        },
        "trend_following": {
            "entry_conditions": {
                "sma_crossover": {"indicator": "sma_20", "operator": ">", "value": 0},
                "trend_strength": {"indicator": "adx", "operator": ">", "value": 25},
                "price_above_ema": {"indicator": "ema_50", "operator": ">", "value": 0}
            },
            "exit_conditions": {
                "trend_reversal": {"indicator": "sma_20", "operator": "<", "value": 0},
                "stop_loss": {"type": "atr_multiplier", "value": 2.5},
                "adx_weak": {"indicator": "adx", "operator": "<", "value": 20}
            },
            "default_parameters": {
                "sma_short": 20,
                "sma_long": 50,
                "ema_period": 50,
                "adx_period": 14,
                "atr_period": 14
            }
        }
    }
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the strategy generator."""
        if seed:
            random.seed(seed)
        self.generation_count = 0
        logger.info(f"StrategyGenerator initialized with seed={seed}")
    
    def generate_random_strategy(
        self,
        strategy_type: Optional[str] = None,
        complexity: int = 2
    ) -> Strategy:
        """Generate a random strategy."""
        if strategy_type is None:
            strategy_type = random.choice(list(self.STRATEGY_TEMPLATES.keys()))
        
        template = self.STRATEGY_TEMPLATES[strategy_type]
        
        entry = self._randomize_conditions(template["entry_conditions"], complexity)
        exit_conds = self._randomize_conditions(template["exit_conditions"], complexity)
        params = self._randomize_parameters(template["default_parameters"])
        indicators = self._extract_indicators(entry, exit_conds)
        
        return Strategy(
            name=f"{strategy_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            strategy_type=strategy_type,
            entry_conditions=entry,
            exit_conditions=exit_conds,
            parameters=params,
            indicators=indicators,
            timeframes=random.choice([['1d'], ['1d', '1w'], ['4h', '1d']]),
            risk_per_trade=random.uniform(0.01, 0.03),
            max_position_size=random.uniform(0.05, 0.15),
            generation=self.generation_count
        )
    
    def _randomize_conditions(
        self,
        template: Dict,
        complexity: int
    ) -> Dict:
        """Randomize condition parameters."""
        conditions = {}
        num_conditions = min(complexity, len(template))
        selected = random.sample(list(template.keys()), num_conditions)
        
        for key in selected:
            cond = deepcopy(template[key])
            if "value" in cond and isinstance(cond["value"], (int, float)):
                cond["value"] *= random.uniform(0.7, 1.3)
            conditions[key] = cond
        
        return conditions
    
    def _randomize_parameters(self, defaults: Dict) -> Dict:
        """Randomize parameter values."""
        params = {}
        for key, value in defaults.items():
            if isinstance(value, int):
                params[key] = max(1, int(value * random.uniform(0.7, 1.3)))
            elif isinstance(value, float):
                params[key] = value * random.uniform(0.7, 1.3)
            else:
                params[key] = value
        return params
    
    def _extract_indicators(self, entry: Dict, exit_conds: Dict) -> List[str]:
        """Extract unique indicators from conditions."""
        indicators = set()
        for cond in list(entry.values()) + list(exit_conds.values()):
            if "indicator" in cond:
                indicators.add(cond["indicator"])
        return list(indicators)
    
    def generate_population(
        self,
        size: int = 20,
        strategy_types: Optional[List[str]] = None
    ) -> List[Strategy]:
        """Generate a population of diverse strategies."""
        if strategy_types is None:
            strategy_types = list(self.STRATEGY_TEMPLATES.keys())
        
        population = []
        for _ in range(size):
            strategy_type = random.choice(strategy_types)
            strategy = self.generate_random_strategy(strategy_type)
            population.append(strategy)
        
        self.generation_count += 1
        logger.info(f"Generated population of {len(population)} strategies")
        return population
    
    def crossover(
        self,
        parent1: Strategy,
        parent2: Strategy
    ) -> Strategy:
        """Create offspring by combining two strategies."""
        child = Strategy(
            name=f"cross_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            strategy_type=random.choice([parent1.strategy_type, parent2.strategy_type]),
            entry_conditions=deepcopy(random.choice([
                parent1.entry_conditions,
                parent2.entry_conditions
            ])),
            exit_conditions=deepcopy(random.choice([
                parent1.exit_conditions,
                parent2.exit_conditions
            ])),
            parameters={**parent1.parameters, **parent2.parameters},
            indicators=list(set(parent1.indicators + parent2.indicators)),
            timeframes=random.choice([parent1.timeframes, parent2.timeframes]),
            risk_per_trade=random.uniform(
                min(parent1.risk_per_trade, parent2.risk_per_trade),
                max(parent1.risk_per_trade, parent2.risk_per_trade)
            ),
            max_position_size=random.uniform(
                min(parent1.max_position_size, parent2.max_position_size),
                max(parent1.max_position_size, parent2.max_position_size)
            ),
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_id=f"{parent1.name}+{parent2.name}"
        )
        
        return child
