"""
Self-Improving Quant AI System - Main orchestration module.

This module provides the SelfImprovingQuantSystem class that orchestrates
the entire self-improving quant trading system including:
- Data scraping
- Strategy generation
- Backtesting
- Evolution
- Continuous learning
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

from learning.strategy_generator import Strategy, StrategyGenerator
from learning.strategy_evaluator import StrategyEvaluator, BacktestResult
from learning.evolution_engine import EvolutionEngine, EvolutionConfig, EvolutionResult

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """Configuration for the self-improving system."""
    symbols: List[str] = field(default_factory=lambda: ['RELIANCE', 'HDFCBANK', 'INFY'])
    population_size: int = 20
    generations: int = 10
    elite_size: int = 3
    mutation_rate: float = 0.15
    min_fitness: float = 0.3
    max_stagnation: int = 3
    data_dir: str = "data/strategies"
    save_interval: int = 5


@dataclass
class SystemState:
    """Current state of the self-improving system."""
    total_strategies_generated: int = 0
    total_backtests_run: int = 0
    best_fitness_achieved: float = 0.0
    last_evolution_time: Optional[datetime] = None
    active_strategies: List[str] = field(default_factory=list)
    archived_strategies: List[str] = field(default_factory=list)


class SelfImprovingQuantSystem:
    """
    Self-improving quantitative trading system.
    
    This system continuously:
    1. Scrapes market data
    2. Generates new trading strategies
    3. Backtests strategies
    4. Evolves the best strategies
    5. Archives underperforming strategies
    
    Usage:
        system = SelfImprovingQuantSystem()
        result = system.evolve_strategies(symbols=['RELIANCE'])
        best = result.best_strategy
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """
        Initialize the self-improving quant system.
        
        Args:
            config: System configuration
        """
        self.config = config or SystemConfig()
        
        self.evolution_config = EvolutionConfig(
            population_size=self.config.population_size,
            generations=self.config.generations,
            elite_size=self.config.elite_size,
            mutation_rate=self.config.mutation_rate,
            min_fitness=self.config.min_fitness,
            max_stagnation=self.config.max_stagnation
        )
        
        self.evaluator = StrategyEvaluator()
        self.evolution_engine = EvolutionEngine(
            config=self.evolution_config,
            evaluator=self.evaluator
        )
        self.generator = StrategyGenerator()
        
        self.state = SystemState()
        
        os.makedirs(self.config.data_dir, exist_ok=True)
        
        logger.info(f"SelfImprovingQuantSystem initialized: {self.config}")
    
    async def scrape_market_data(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scrape market data for given symbols.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to data
        """
        if symbols is None:
            symbols = self.config.symbols
        
        logger.info(f"Scraping market data for {len(symbols)} symbols")
        
        data = {}
        for symbol in symbols:
            try:
                import yfinance as yf
                ticker = yf.Ticker(f"{symbol}.NS")
                hist = ticker.history(period="2y")
                
                if not hist.empty:
                    hist = self._add_indicators(hist)
                    data[symbol] = hist
                    logger.info(f"Fetched {len(hist)} data points for {symbol}")
                else:
                    logger.warning(f"No data fetched for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
        
        self.state.total_backtests_run += len(data)
        return data
    
    def _add_indicators(self, df):
        """Add technical indicators to data."""
        import pandas as pd
        import numpy as np
        
        df = df.copy()
        
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['sma_50'] = df['Close'].rolling(50).mean()
        df['sma_200'] = df['Close'].rolling(200).mean()
        
        df['ema_12'] = df['Close'].ewm(span=12).mean()
        df['ema_26'] = df['Close'].ewm(span=26).mean()
        
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(9).mean()
        
        sma = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['bb_upper'] = sma + (2 * std)
        df['bb_lower'] = sma - (2 * std)
        
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        df['volume_sma'] = df['Volume'].rolling(20).mean()
        
        df = df.dropna()
        
        return df
    
    def evolve_strategies(
        self,
        symbols: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None
    ) -> EvolutionResult:
        """
        Run the evolution process to improve strategies.
        
        Args:
            symbols: Stock symbols to optimize for
            data: Optional pre-fetched data
            progress_callback: Progress callback
            
        Returns:
            EvolutionResult with best strategy
        """
        if symbols is None:
            symbols = self.config.symbols
        
        logger.info(f"Starting strategy evolution for {symbols}")
        
        async def fetch_data():
            return await self.scrape_market_data(symbols)
        
        if data is None:
            try:
                data = asyncio.run(fetch_data())
            except Exception as e:
                logger.warning(f"Could not fetch data: {e}")
                data = {}
        
        def data_provider(symbol):
            return data.get(symbol)
        
        self.evolution_engine.data_provider = data_provider
        
        result = self.evolution_engine.evolve(symbols, data, progress_callback)
        
        self.state.total_strategies_generated += self.config.population_size * self.config.generations
        self.state.best_fitness_achieved = max(
            self.state.best_fitness_achieved,
            result.best_result.fitness
        )
        self.state.last_evolution_time = datetime.now()
        
        if result.best_result.fitness >= self.config.min_fitness:
            self.state.active_strategies.append(result.best_strategy.name)
        
        self._save_evolution_result(result)
        
        logger.info(f"Evolution complete! Best fitness: {result.best_result.fitness:.4f}")
        
        return result
    
    def generate_and_test_strategies(
        self,
        n_strategies: int = 10,
        symbols: Optional[List[str]] = None
    ) -> List[tuple]:
        """
        Generate and test a batch of strategies.
        
        Args:
            n_strategies: Number of strategies to generate
            symbols: Symbols to test on
            
        Returns:
            List of (strategy, result) tuples
        """
        if symbols is None:
            symbols = self.config.symbols
        
        data = asyncio.run(self.scrape_market_data(symbols))
        
        strategies = self.generator.generate_population(n_strategies)
        
        results = []
        for strategy in strategies:
            result = self.evaluator.evaluate(strategy, data[symbols[0]])
            strategy.fitness = result.fitness
            results.append((strategy, result))
        
        results.sort(key=lambda x: x[1].fitness, reverse=True)
        
        return results
    
    def run_continuous_learning(
        self,
        intervals: int = 5,
        delay_seconds: int = 3600
    ):
        """
        Run continuous learning loop.
        
        Args:
            intervals: Number of evolution cycles
            delay_seconds: Delay between cycles
            
        Note: This is a blocking call.
        """
        logger.info(f"Starting continuous learning: {intervals} intervals")
        
        for i in range(intervals):
            logger.info(f"=== Learning Cycle {i + 1}/{intervals} ===")
            
            result = self.evolve_strategies()
            
            logger.info(f"Cycle {i + 1} complete: Best fitness = {result.best_result.fitness:.4f}")
            
            if i < intervals - 1:
                logger.info(f"Waiting {delay_seconds}s before next cycle...")
                import time
                time.sleep(delay_seconds)
        
        logger.info("Continuous learning complete!")
        
        return self.evolution_engine.get_best_strategies(10)
    
    def _save_evolution_result(self, result: EvolutionResult):
        """Save evolution result to file."""
        filepath = os.path.join(
            self.config.data_dir,
            f"evolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'best_strategy': result.best_strategy.to_dict(),
            'best_result': result.best_result.to_dict(),
            'generation': result.generation,
            'total_generations': result.total_generations,
            'evolution_time': result.evolution_time_seconds,
            'history': result.history
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved evolution result to {filepath}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            'config': {
                'symbols': self.config.symbols,
                'population_size': self.config.population_size,
                'generations': self.config.generations
            },
            'state': {
                'total_strategies_generated': self.state.total_strategies_generated,
                'total_backtests_run': self.state.total_backtests_run,
                'best_fitness_achieved': self.state.best_fitness_achieved,
                'last_evolution_time': self.state.last_evolution_time.isoformat() if self.state.last_evolution_time else None,
                'active_strategies_count': len(self.state.active_strategies),
                'archived_strategies_count': len(self.state.archived_strategies)
            },
            'best_strategies': self.evolution_engine.get_best_strategies(5)
        }
    
    def export_strategies(self, filepath: str):
        """Export best strategies to file."""
        self.evolution_engine.save_best_strategies(filepath)
    
    def load_strategies(self, filepath: str) -> List[Strategy]:
        """Load strategies from file."""
        return self.evolution_engine.load_strategies(filepath)


def create_evolution_cli():
    """Create CLI for running evolution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Self-Improving Quant System')
    parser.add_argument('--symbols', type=str, default='RELIANCE,HDFCBANK,INFY',
                        help='Comma-separated stock symbols')
    parser.add_argument('--population', type=int, default=20,
                        help='Population size')
    parser.add_argument('--generations', type=int, default=10,
                        help='Number of generations')
    parser.add_argument('--mutation', type=float, default=0.15,
                        help='Mutation rate')
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(',')
    
    config = SystemConfig(
        symbols=symbols,
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation
    )
    
    system = SelfImprovingQuantSystem(config)
    
    def progress(gen, total, fitness):
        print(f"Generation {gen + 1}/{total}: Best Fitness = {fitness:.4f}")
    
    result = system.evolve_strategies(progress_callback=progress)
    
    print("\n" + "="*60)
    print("EVOLUTION COMPLETE")
    print("="*60)
    print(f"Best Strategy: {result.best_strategy.name}")
    print(f"Strategy Type: {result.best_strategy.strategy_type}")
    print(f"Fitness: {result.best_result.fitness:.4f}")
    print(f"Total Return: {result.best_result.total_return:.2%}")
    print(f"Sharpe Ratio: {result.best_result.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {result.best_result.max_drawdown:.2%}")
    print(f"Win Rate: {result.best_result.win_rate:.2%}")
    print(f"Total Trades: {result.best_result.total_trades}")
    print(f"Evolution Time: {result.evolution_time_seconds:.1f}s")
    print("="*60)
    
    system.export_strategies(f"best_strategy_{datetime.now().strftime('%Y%m%d')}.json")


if __name__ == '__main__':
    create_evolution_cli()
