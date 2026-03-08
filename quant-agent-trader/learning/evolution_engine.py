"""
Evolution Engine - Genetic algorithm for evolving trading strategies.

This module provides the EvolutionEngine class that implements genetic algorithms
to evolve and improve trading strategies over multiple generations.
"""

import logging
import random
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from copy import deepcopy

from learning.strategy_generator import Strategy, StrategyGenerator
from learning.strategy_evaluator import StrategyEvaluator, BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class EvolutionConfig:
    """Configuration for the evolution process."""
    population_size: int = 20
    generations: int = 10
    elite_size: int = 3
    mutation_rate: float = 0.15
    crossover_rate: float = 0.3
    tournament_size: int = 3
    min_fitness: float = 0.3
    max_stagnation: int = 3


@dataclass
class EvolutionResult:
    """Results from an evolution run."""
    best_strategy: Strategy
    best_result: BacktestResult
    generation: int
    total_generations: int
    final_population: List[Strategy]
    all_time_best: Strategy
    all_time_best_result: BacktestResult
    evolution_time_seconds: float
    stagnation_count: int
    history: List[Dict[str, Any]] = field(default_factory=list)


class EvolutionEngine:
    """
    Genetic algorithm engine for evolving trading strategies.
    
    Features:
    - Tournament selection
    - Elite preservation
    - Crossover and mutation
    - Adaptive mutation rates
    - Early stopping on stagnation
    """
    
    def __init__(
        self,
        config: Optional[EvolutionConfig] = None,
        evaluator: Optional[StrategyEvaluator] = None,
        data_provider: Optional[Callable] = None
    ):
        """
        Initialize the evolution engine.
        
        Args:
            config: Evolution configuration
            evaluator: Strategy evaluator instance
            data_provider: Function that returns historical data
        """
        self.config = config or EvolutionConfig()
        self.evaluator = evaluator or StrategyEvaluator()
        self.data_provider = data_provider
        self.generator = StrategyGenerator()
        
        self.current_generation = 0
        self.stagnation_count = 0
        self.all_time_best: Optional[Strategy] = None
        self.all_time_best_result: Optional[BacktestResult] = None
        self.history: List[Dict[str, Any]] = []
        
        logger.info(f"EvolutionEngine initialized: {self.config}")
    
    def evolve(
        self,
        symbols: List[str],
        data: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> EvolutionResult:
        """
        Run the evolution process.
        
        Args:
            symbols: List of stock symbols to backtest on
            data: Optional pre-fetched data
            progress_callback: Optional callback for progress updates
            
        Returns:
            EvolutionResult with best strategy and details
        """
        import time
        start_time = time.time()
        
        logger.info(f"Starting evolution: {self.config.generations} generations, population={self.config.population_size}")
        
        population = self.generator.generate_population(self.config.population_size)
        
        best_overall = None
        best_overall_result = None
        stagnation_count = 0
        
        for gen in range(self.config.generations):
            self.current_generation = gen
            logger.info(f"=== Generation {gen + 1}/{self.config.generations} ===")
            
            evaluated = self._evaluate_population(population, symbols, data)
            
            evaluated.sort(key=lambda x: x[1].fitness, reverse=True)
            
            best_strategy, best_result = evaluated[0]
            
            if best_overall is None or best_result.fitness > best_overall_result.fitness:
                best_overall = deepcopy(best_strategy)
                best_overall_result = best_result
                best_overall.fitness = best_result.fitness
                stagnation_count = 0
                logger.info(f"New best! Fitness: {best_result.fitness:.4f}, Return: {best_result.total_return:.2%}")
            else:
                stagnation_count += 1
                logger.info(f"Stagnation: {stagnation_count}")
            
            self.history.append({
                'generation': gen,
                'best_fitness': best_result.fitness,
                'best_return': best_result.total_return,
                'avg_fitness': sum(r.fitness for _, r in evaluated) / len(evaluated),
                'best_strategy': best_strategy.name
            })
            
            if progress_callback:
                progress_callback(gen, self.config.generations, best_result.fitness)
            
            if stagnation_count >= self.config.max_stagnation:
                logger.info(f"Early stopping: {stagnation_count} generations without improvement")
                break
            
            population = self._create_next_generation(evaluated)
        
        evolution_time = time.time() - start_time
        
        logger.info(f"Evolution complete! Best fitness: {best_overall_result.fitness:.4f}")
        
        return EvolutionResult(
            best_strategy=best_overall,
            best_result=best_overall_result,
            generation=self.current_generation,
            total_generations=self.config.generations,
            final_population=population,
            all_time_best=best_overall,
            all_time_best_result=best_overall_result,
            evolution_time_seconds=evolution_time,
            stagnation_count=stagnation_count,
            history=self.history
        )
    
    def _evaluate_population(
        self,
        population: List[Strategy],
        symbols: List[str],
        data: Optional[Dict[str, Any]]
    ) -> List[tuple]:
        """Evaluate all strategies in the population."""
        results = []
        
        for strategy in population:
            try:
                result = self._evaluate_strategy(strategy, symbols, data)
                strategy.fitness = result.fitness
                results.append((strategy, result))
            except Exception as e:
                logger.warning(f"Error evaluating {strategy.name}: {e}")
                strategy.fitness = 0.0
                results.append((strategy, BacktestResult(
                    strategy_name=strategy.name,
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
                    equity_curve=[100000]
                )))
        
        return results
    
    def _evaluate_strategy(
        self,
        strategy: Strategy,
        symbols: List[str],
        data: Optional[Dict[str, Any]]
    ) -> BacktestResult:
        """Evaluate a single strategy."""
        if self.data_provider:
            data = self.data_provider(symbols[0])
            if data is not None:
                return self.evaluator.evaluate(strategy, data)
        
        if data is None and symbols:
            import yfinance as yf
            ticker = yf.Ticker(symbols[0])
            hist = ticker.history(period="2y")
            if not hist.empty:
                return self.evaluator.evaluate(strategy, hist)
        
        return BacktestResult(
            strategy_name=strategy.name,
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
            equity_curve=[self.evaluator.initial_capital]
        )
    
    def _create_next_generation(
        self,
        evaluated: List[tuple]
    ) -> List[Strategy]:
        """Create the next generation using genetic operators."""
        population = []
        
        elite = [s for s, r in evaluated[:self.config.elite_size] if r.fitness >= self.config.min_fitness]
        population.extend([deepcopy(s) for s in elite])
        
        while len(population) < self.config.population_size:
            parent1 = self._tournament_select(evaluated)
            parent2 = self._tournament_select(evaluated)
            
            if random.random() < self.config.crossover_rate and parent1 != parent2:
                child = self.generator.crossover(parent1, parent2)
            else:
                child = deepcopy(parent1)
            
            if random.random() < self.config.mutation_rate:
                child = child.mutate(self.config.mutation_rate)
            
            population.append(child)
        
        return population[:self.config.population_size]
    
    def _tournament_select(self, evaluated: List[tuple]) -> Strategy:
        """Select a strategy using tournament selection."""
        tournament = random.sample(evaluated, min(self.config.tournament_size, len(evaluated)))
        tournament.sort(key=lambda x: x[1].fitness, reverse=True)
        return tournament[0][0]
    
    def get_best_strategies(
        self,
        n: int = 5
    ) -> List[Dict[str, Any]]:
        """Get the top N best strategies from history."""
        if not self.history:
            return []
        
        sorted_history = sorted(self.history, key=lambda x: x['best_fitness'], reverse=True)
        return sorted_history[:n]
    
    def export_strategy(self, strategy: Strategy) -> Dict[str, Any]:
        """Export strategy to dictionary for storage."""
        return strategy.to_dict()
    
    def import_strategy(self, data: Dict[str, Any]) -> Strategy:
        """Import strategy from dictionary."""
        strategy = Strategy(
            name=data['name'],
            strategy_type=data['strategy_type'],
            entry_conditions=data['entry_conditions'],
            exit_conditions=data['exit_conditions'],
            parameters=data['parameters'],
            indicators=data['indicators'],
            timeframes=data['timeframes'],
            risk_per_trade=data.get('risk_per_trade', 0.02),
            max_position_size=data.get('max_position_size', 0.1),
            generation=data.get('generation', 0),
            fitness=data.get('fitness', 0.0)
        )
        return strategy
    
    def save_best_strategies(self, filepath: str):
        """Save best strategies to file."""
        import json
        if self.all_time_best:
            data = self.export_strategy(self.all_time_best)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved best strategy to {filepath}")
    
    def load_strategies(self, filepath: str) -> List[Strategy]:
        """Load strategies from file."""
        import json
        strategies = []
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for d in data:
                        strategies.append(self.import_strategy(d))
                else:
                    strategies.append(self.import_strategy(data))
            logger.info(f"Loaded {len(strategies)} strategies from {filepath}")
        except Exception as e:
            logger.error(f"Error loading strategies: {e}")
        return strategies
