"""
Self-Evaluation Loop - Agents learn from their past performance.

After each trade, stores:
- Agent signals
- Decision
- Profit/Loss
- Holding period

Then computes:
- Agent accuracy
- Agent Sharpe contribution
- Can remove weak agents

Usage:
    evaluator = AgentEvaluator()
    
    # After trade
    evaluator.record_trade(
        symbol="TCS",
        signals=[agent_signal_1, agent_signal_2],
        decision="buy",
        pnl=1000,
        holding_period=5
    )
    
    # Get agent performance
    performance = evaluator.get_agent_performance()
    
    # Get weak agents to remove
    weak = evaluator.get_weak_agents(threshold=0.45)
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
import json
import logging

from signals.signal_schema import AgentSignal

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a single trade with all agent signals."""
    trade_id: str
    symbol: str
    decision: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    holding_period: int
    timestamp: datetime
    agent_signals: List[Dict]
    regime: str = "unknown"


@dataclass
class AgentPerformance:
    """Performance metrics for an agent."""
    agent_name: str
    total_signals: int
    winning_signals: int
    accuracy: float
    avg_confidence: float
    avg_score: float
    sharpe_contribution: float
    pnl_contribution: float


class AgentEvaluator:
    """
    Self-evaluation system for agents.
    
    Tracks agent performance over time and identifies weak agents.
    """
    
    def __init__(self, storage_path: str = "data/agent_evaluation"):
        self.storage_path = storage_path
        self.trade_records: List[TradeRecord] = []
        self._load_history()
    
    def record_trade(
        self,
        symbol: str,
        signals: List[AgentSignal],
        decision: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        holding_period: int,
        regime: str = "unknown"
    ) -> None:
        """
        Record a completed trade with all agent signals.
        
        Args:
            symbol: Stock symbol
            signals: List of agent signals that contributed
            decision: Final decision (buy/sell/hold)
            entry_price: Entry price
            exit_price: Exit price
            pnl: Profit/loss
            holding_period: Days held
            regime: Market regime
        """
        trade_id = f"TRADE_{len(self.trade_records):06d}"
        
        pnl_percent = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
        
        signal_dicts = []
        for signal in signals:
            signal_dicts.append({
                "agent_name": signal.agent_name,
                "agent_category": signal.agent_category,
                "signal": signal.signal,
                "confidence": signal.confidence,
                "numerical_score": signal.numerical_score,
                "reasoning": signal.reasoning
            })
        
        record = TradeRecord(
            trade_id=trade_id,
            symbol=symbol,
            decision=decision,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            pnl_percent=pnl_percent,
            holding_period=holding_period,
            timestamp=datetime.now(),
            agent_signals=signal_dicts,
            regime=regime
        )
        
        self.trade_records.append(record)
        
        self._save_history()
    
    def get_agent_performance(
        self,
        min_signals: int = 5
    ) -> Dict[str, AgentPerformance]:
        """
        Calculate performance metrics for each agent.
        
        Args:
            min_signals: Minimum signals required for evaluation
            
        Returns:
            Dict of agent_name -> AgentPerformance
        """
        agent_data: Dict[str, Dict] = {}
        
        for trade in self.trade_records:
            for signal in trade.agent_signals:
                agent_name = signal["agent_name"]
                
                if agent_name not in agent_data:
                    agent_data[agent_name] = {
                        "signals": [],
                        "correct": 0,
                        "total": 0,
                        "confidences": [],
                        "scores": [],
                        "pnl_contribution": 0
                    }
                
                agent_data[agent_name]["signals"].append(signal)
                agent_data[agent_name]["total"] += 1
                agent_data[agent_name]["confidences"].append(signal["confidence"])
                agent_data[agent_name]["scores"].append(signal["numerical_score"])
                
                signal_direction = signal["signal"].lower()
                trade_direction = "buy" if trade.pnl > 0 else "sell"
                
                if signal_direction == trade_direction:
                    agent_data[agent_name]["correct"] += 1
                
                contribution = trade.pnl * abs(signal["numerical_score"]) / 100
                agent_data[agent_name]["pnl_contribution"] += contribution
        
        performance = {}
        
        for agent_name, data in agent_data.items():
            if data["total"] < min_signals:
                continue
            
            accuracy = data["correct"] / data["total"] if data["total"] > 0 else 0
            
            sharpe_contrib = self._calculate_sharpe_contribution(data["signals"])
            
            perf = AgentPerformance(
                agent_name=agent_name,
                total_signals=data["total"],
                winning_signals=data["correct"],
                accuracy=accuracy,
                avg_confidence=np.mean(data["confidences"]),
                avg_score=np.mean(data["scores"]),
                sharpe_contribution=sharpe_contrib,
                pnl_contribution=data["pnl_contribution"]
            )
            
            performance[agent_name] = perf
        
        return performance
    
    def _calculate_sharpe_contribution(self, signals: List[Dict]) -> float:
        """Calculate Sharpe ratio contribution from signals."""
        if not signals:
            return 0
        
        scores = [s["numerical_score"] for s in signals]
        
        if len(scores) < 2:
            return 0
        
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        
        if std_score == 0:
            return 0
        
        sharpe = mean_score / std_score * np.sqrt(252)
        
        return sharpe
    
    def get_weak_agents(
        self,
        threshold: float = 0.45,
        min_signals: int = 10
    ) -> List[str]:
        """
        Get list of weak agents to potentially remove.
        
        Args:
            threshold: Accuracy threshold below which agent is weak
            min_signals: Minimum signals required
            
        Returns:
            List of weak agent names
        """
        performance = self.get_agent_performance(min_signals)
        
        weak = []
        
        for agent_name, perf in performance.items():
            if perf.accuracy < threshold:
                weak.append(agent_name)
        
        weak.sort(key=lambda a: performance[a].accuracy)
        
        return weak
    
    def get_strong_agents(
        self,
        threshold: float = 0.60,
        min_signals: int = 10
    ) -> List[str]:
        """Get list of strong agents."""
        performance = self.get_agent_performance(min_signals)
        
        strong = []
        
        for agent_name, perf in performance.items():
            if perf.accuracy >= threshold:
                strong.append(agent_name)
        
        strong.sort(key=lambda a: performance[a].accuracy, reverse=True)
        
        return strong
    
    def get_agent_category_performance(self) -> Dict[str, Dict]:
        """Get performance aggregated by agent category."""
        performance = self.get_agent_performance()
        
        category_data: Dict[str, Dict] = {}
        
        for agent_name, perf in performance.items():
            category = agent_name.replace("_agent", "").replace("_", " ")
            
            if category not in category_data:
                category_data[category] = {
                    "total_signals": 0,
                    "total_correct": 0,
                    "agents": []
                }
            
            category_data[category]["total_signals"] += perf.total_signals
            category_data[category]["total_correct"] += int(perf.winning_signals)
            category_data[category]["agents"].append(agent_name)
        
        for category, data in category_data.items():
            if data["total_signals"] > 0:
                data["accuracy"] = data["total_correct"] / data["total_signals"]
            else:
                data["accuracy"] = 0
        
        return category_data
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for improving the system."""
        weak_agents = self.get_weak_agents(threshold=0.45)
        strong_agents = self.get_strong_agents(threshold=0.60)
        
        category_perf = self.get_agent_category_performance()
        
        best_category = max(
            category_perf.items(),
            key=lambda x: x[1].get("accuracy", 0)
        ) if category_perf else (None, {})
        
        worst_category = min(
            category_perf.items(),
            key=lambda x: x[1].get("accuracy", 0)
        ) if category_perf else (None, {})
        
        recommendations = {
            "weak_agents_to_remove": weak_agents[:5],
            "strong_agents": strong_agents[:10],
            "best_category": best_category[0],
            "best_category_accuracy": best_category[1].get("accuracy", 0),
            "worst_category": worst_category[0],
            "worst_category_accuracy": worst_category[1].get("accuracy", 0),
            "total_trades": len(self.trade_records)
        }
        
        return recommendations
    
    def _save_history(self) -> None:
        """Save trade history to disk."""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        filepath = f"{self.storage_path}/trade_history.json"
        
        records = []
        for trade in self.trade_records:
            records.append({
                "trade_id": trade.trade_id,
                "symbol": trade.symbol,
                "decision": trade.decision,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "pnl": trade.pnl,
                "pnl_percent": trade.pnl_percent,
                "holding_period": trade.holding_period,
                "timestamp": trade.timestamp.isoformat(),
                "agent_signals": trade.agent_signals,
                "regime": trade.regime
            })
        
        with open(filepath, "w") as f:
            json.dump(records, f, indent=2)
    
    def _load_history(self) -> None:
        """Load trade history from disk."""
        import os
        
        filepath = f"{self.storage_path}/trade_history.json"
        
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, "r") as f:
                records = json.load(f)
            
            for r in records:
                trade = TradeRecord(
                    trade_id=r["trade_id"],
                    symbol=r["symbol"],
                    decision=r["decision"],
                    entry_price=r["entry_price"],
                    exit_price=r["exit_price"],
                    pnl=r["pnl"],
                    pnl_percent=r["pnl_percent"],
                    holding_period=r["holding_period"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    agent_signals=r["agent_signals"],
                    regime=r.get("regime", "unknown")
                )
                self.trade_records.append(trade)
            
            logger.info(f"Loaded {len(self.trade_records)} trade records")
        
        except Exception as e:
            logger.warning(f"Could not load trade history: {e}")
    
    def generate_report(self) -> str:
        """Generate a text report of agent performance."""
        perf = self.get_agent_performance()
        
        lines = []
        lines.append("=" * 60)
        lines.append("AGENT PERFORMANCE REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        lines.append(f"Total Trades: {len(self.trade_records)}")
        lines.append("")
        
        lines.append("TOP PERFORMERS:")
        sorted_perf = sorted(perf.values(), key=lambda x: x.accuracy, reverse=True)
        for p in sorted_perf[:10]:
            lines.append(f"  {p.agent_name}: {p.accuracy:.1%} accuracy ({p.total_signals} signals)")
        
        lines.append("")
        lines.append("WEAK AGENTS (consider removing):")
        weak = self.get_weak_agents(threshold=0.45)
        for a in weak[:5]:
            lines.append(f"  {a}: {perf[a].accuracy:.1%} accuracy")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)


class AdaptiveWeightOptimizer:
    """
    Optimizes agent weights based on performance.
    
    After collecting enough trades, adjusts weights to favor
    better-performing agents.
    """
    
    def __init__(self, evaluator: AgentEvaluator):
        self.evaluator = evaluator
        self.base_weights: Dict[str, float] = {
            "technical": 0.30,
            "fundamental": 0.25,
            "sentiment": 0.15,
            "macro": 0.10,
            "market_structure": 0.10,
            "risk": 0.10
        }
    
    def optimize_weights(
        self,
        boost_factor: float = 1.5,
        decay_factor: float = 0.7
    ) -> Dict[str, float]:
        """
        Optimize category weights based on performance.
        
        Args:
            boost_factor: Multiply good category weight
            decay_factor: Multiply poor category weight
            
        Returns:
            Optimized weights
        """
        category_perf = self.evaluator.get_agent_category_performance()
        
        if not category_perf:
            return self.base_weights.copy()
        
        avg_accuracy = np.mean([c.get("accuracy", 0) for c in category_perf.values()])
        
        optimized = {}
        
        for category, data in category_perf.items():
            accuracy = data.get("accuracy", 0)
            
            if accuracy > avg_accuracy * 1.1:
                weight_mult = boost_factor
            elif accuracy < avg_accuracy * 0.9:
                weight_mult = decay_factor
            else:
                weight_mult = 1.0
            
            base_cat = category.split()[0].lower()
            base_weight = self.base_weights.get(base_cat, 0.1)
            
            optimized[base_cat] = base_weight * weight_mult
        
        total = sum(optimized.values())
        optimized = {k: v / total for k, v in optimized.items()}
        
        return optimized
    
    def get_adjustment_summary(self) -> Dict[str, Any]:
        """Get summary of weight adjustments."""
        optimized = self.optimize_weights()
        
        adjustments = {}
        for cat, weight in optimized.items():
            base = self.base_weights.get(cat, 0.1)
            change = (weight - base) / base * 100
            adjustments[cat] = {
                "old_weight": base,
                "new_weight": weight,
                "change_pct": change
            }
        
        return adjustments
