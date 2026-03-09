"""
Research CLI - Strategy experimentation and analysis.

Usage:
    python main.py research --symbol TCS --start 2018 --end 2024
    python main.py research --symbols RELIANCE,TCS --start 2020 --end 2024 --output results/
    python main.py research --symbol NIFTY 50 --regime-analysis

Pipeline:
    1. Load historical data
    2. Run agents
    3. Store signals
    4. Run backtest
    5. Generate report
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import numpy as np

from config.settings import config as system_config
from backtesting.engine import BacktestEngine, BacktestConfigExtended
from signals.signal_aggregator import SignalAggregator
from signals.signal_schema import AgentSignal
from signals.feature_extractor import FeatureExtractor
from data.feature_store import FeatureStore
from models.meta_model import WalkForwardTrainer, ModelRegistry
from utils.structured_logging import get_logger, LogLayer, configure_logging

logger = get_logger(__name__, LogLayer.BACKTEST)


class ResearchReport:
    """Generates research reports from backtest results."""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(
        self,
        config: Dict[str, Any],
        backtest_results: Dict[str, Any],
        signal_analysis: Optional[Dict[str, Any]] = None,
        feature_importance: Optional[pd.DataFrame] = None,
        walk_forward_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive research report."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report = {
            "config": config,
            "timestamp": timestamp,
            "performance": self._extract_performance(backtest_results),
            "signal_analysis": signal_analysis or {},
            "feature_importance": feature_importance.to_dict() if feature_importance is not None else {},
            "walk_forward": walk_forward_results or {}
        }
        
        report_file = self.output_dir / f"research_report_{timestamp}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report saved to {report_file}")
        
        self._print_summary(report)
        
        return report
    
    def _extract_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract performance metrics."""
        metrics = results.get("metrics", {})
        
        return {
            "total_return": metrics.get("cumulative_return", 0),
            "annualized_return": metrics.get("annualized_return", 0),
            "sharpe_ratio": metrics.get("sharpe_ratio", 0),
            "sortino_ratio": metrics.get("sortino_ratio", 0),
            "max_drawdown": metrics.get("max_drawdown", 0),
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor", 0),
            "total_trades": metrics.get("total_trades", 0),
            "avg_holding_period": metrics.get("avg_holding_period", 0)
        }
    
    def _print_summary(self, report: Dict[str, Any]) -> None:
        """Print summary to console."""
        print("\n" + "="*60)
        print("RESEARCH SUMMARY")
        print("="*60)
        
        perf = report.get("performance", {})
        
        print(f"\nPerformance Metrics:")
        print(f"  Total Return:     {perf.get('total_return', 0)*100:.2f}%")
        print(f"  Annual Return:    {perf.get('annualized_return', 0)*100:.2f}%")
        print(f"  Sharpe Ratio:    {perf.get('sharpe_ratio', 0):.2f}")
        print(f"  Sortino Ratio:    {perf.get('sortino_ratio', 0):.2f}")
        print(f"  Max Drawdown:     {perf.get('max_drawdown', 0)*100:.2f}%")
        print(f"  Win Rate:         {perf.get('win_rate', 0)*100:.2f}%")
        print(f"  Profit Factor:    {perf.get('profit_factor', 0):.2f}")
        print(f"  Total Trades:     {perf.get('total_trades', 0)}")
        
        wf = report.get("walk_forward", {})
        if wf:
            summary = wf.get("summary", {})
            print(f"\nWalk-Forward Validation:")
            print(f"  Avg Accuracy:     {summary.get('avg_accuracy', 0):.2%}")
            print(f"  Avg Sharpe:      {summary.get('avg_sharpe_ratio', 0):.2f}")
        
        print("\n" + "="*60)


class ResearchEngine:
    """
    Research engine for strategy experimentation.
    
    Usage:
        engine = ResearchEngine()
        results = engine.run(
            symbols=["TCS", "RELIANCE"],
            start_date=datetime(2018, 1, 1),
            end_date=datetime(2024, 1, 1)
        )
    """
    
    def __init__(
        self,
        agents: Optional[List[Any]] = None,
        output_dir: str = "results"
    ):
        self.agents = agents
        self.output_dir = output_dir
        self.feature_store = FeatureStore()
        self.report_generator = ResearchReport(output_dir)
    
    def run(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000,
        generate_features: bool = True,
        walk_forward: bool = False,
        regime_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        Run full research pipeline.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date
            end_date: End date
            initial_capital: Initial capital
            generate_features: Generate training data
            walk_forward: Run walk-forward validation
            regime_analysis: Analyze by regime
            
        Returns:
            Research results
        """
        logger.info(f"Starting research: {symbols} from {start_date} to {end_date}")
        
        from main import QuantTradingSystem
        system = QuantTradingSystem()
        
        data = {}
        for symbol in symbols:
            logger.info(f"Loading data for {symbol}")
            df = asyncio_run(system.fetch_market_data(symbol, days=3650))
            if df is not None and not df.empty:
                data[symbol] = df
        
        if not data:
            logger.error("No data loaded")
            return {}
        
        logger.info(f"Running backtest on {len(symbols)} symbols")
        
        engine = BacktestEngine()
        results = engine.run_backtest(
            data=data,
            agents=self.agents or system.agents,
            start_date=start_date,
            end_date=end_date,
            regime="sideways"
        )
        
        signal_analysis = {}
        if generate_features:
            logger.info("Generating training features")
            from data.training_data_generator import TrainingDataGenerator
            
            generator = TrainingDataGenerator()
            dataset = generator.generate(
                data=data,
                agents=self.agents or system.agents,
                start_date=start_date,
                end_date=end_date,
                symbols=symbols
            )
            
            if not dataset.empty:
                signal_analysis = self._analyze_signals(dataset)
        
        feature_importance = None
        walk_forward_results = None
        
        if walk_forward:
            logger.info("Running walk-forward validation")
            dataset = self.feature_store.read_features(start_date, end_date)
            
            if len(dataset) > 1000:
                wft = WalkForwardTrainer(train_years=3, test_years=1)
                walk_forward_results = wft.run_walk_forward(
                    dataset, 
                    target="target_binary_5d"
                )
                
                if walk_forward_results:
                    feature_importance = self._get_feature_importance(dataset)
        
        config = {
            "symbols": symbols,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_capital": initial_capital
        }
        
        backtest_dict = {
            "metrics": {
                "cumulative_return": results.metrics.cumulative_return,
                "annualized_return": results.metrics.annualized_return,
                "sharpe_ratio": results.metrics.sharpe_ratio,
                "sortino_ratio": results.metrics.sortino_ratio,
                "max_drawdown": results.metrics.max_drawdown,
                "win_rate": results.metrics.win_rate,
                "profit_factor": results.metrics.profit_factor,
                "total_trades": results.metrics.total_trades,
                "avg_holding_period": results.metrics.avg_holding_period
            }
        }
        
        report = self.report_generator.generate_report(
            config=config,
            backtest_results=backtest_dict,
            signal_analysis=signal_analysis,
            feature_importance=feature_importance,
            walk_forward_results=walk_forward_results
        )
        
        return report
    
    def _analyze_signals(self, dataset: pd.DataFrame) -> Dict[str, Any]:
        """Analyze signal performance."""
        analysis = {}
        
        feature_cols = [c for c in dataset.columns if c.endswith("_score")]
        
        if feature_cols and "target_binary_5d" in dataset.columns:
            correlations = {}
            for col in feature_cols:
                corr = dataset[col].corr(dataset["target_binary_5d"])
                correlations[col] = float(corr)
            
            analysis["signal_correlations"] = correlations
            
            top_signals = sorted(
                correlations.items(), 
                key=lambda x: abs(x[1]), 
                reverse=True
            )[:5]
            analysis["top_signals"] = top_signals
        
        return analysis
    
    def _get_feature_importance(self, dataset: pd.DataFrame) -> pd.DataFrame:
        """Train model and get feature importance."""
        from models.meta_model import MetaModelTrainer
        
        target = "target_binary_5d"
        
        exclude = ["timestamp", "symbol", "date", "target_binary_5d", 
                   "target_binary_10d", "target_binary_20d",
                   "future_return_5d", "future_return_10d", "future_return_20d"]
        
        features = [c for c in dataset.columns if c not in exclude 
                    and dataset[c].dtype in [np.float64, np.int64]]
        
        df = dataset.dropna(subset=[target] + features)
        
        if len(df) < 100:
            return pd.DataFrame()
        
        trainer = MetaModelTrainer(model_type="lightgbm")
        trainer.train(df, target=target, feature_cols=features)
        
        return trainer.get_feature_importance()


def asyncio_run(coro):
    """Run async code in sync context."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def run_research_cli():
    """Entry point for research CLI."""
    parser = argparse.ArgumentParser(
        description="Research Mode - Strategy experimentation"
    )
    
    parser.add_argument(
        "--symbol", "-s",
        type=str,
        help="Single symbol (or use --symbols)"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated symbols"
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2018-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2024-01-01",
        help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=100000,
        help="Initial capital"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="results",
        help="Output directory"
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Run walk-forward validation"
    )
    parser.add_argument(
        "--regime-analysis",
        action="store_true",
        help="Analyze by market regime"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        configure_logging(level=logging.DEBUG)
    
    symbols = []
    if args.symbol:
        symbols = [args.symbol]
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    else:
        print("Error: Must specify --symbol or --symbols")
        sys.exit(1)
    
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")
    
    engine = ResearchEngine(output_dir=args.output)
    
    results = engine.run(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.capital,
        walk_forward=args.walk_forward,
        regime_analysis=args.regime_analysis
    )
    
    return results


if __name__ == "__main__":
    run_research_cli()
