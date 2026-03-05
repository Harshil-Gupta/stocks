"""
Reinforcement Learning Feedback System for Multi-Agent Quant Trading.

This module provides the RLFeedbackSystem class that implements reinforcement
learning concepts to improve agent signal quality over time through feedback loops.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Deque
from collections import deque
from datetime import datetime
import logging
import math
import random

from signals.signal_schema import TradeResult


logger = logging.getLogger(__name__)


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent."""
    agent_name: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    avg_holding_period: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    win_rate: float = 0.0
    avg_pnl_per_trade: float = 0.0
    sharpe_approximation: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl": self.total_pnl,
            "total_pnl_percent": self.total_pnl_percent,
            "avg_holding_period": self.avg_holding_period,
            "win_rate": self.win_rate,
            "avg_pnl_per_trade": self.avg_pnl_per_trade,
            "sharpe_approximation": self.sharpe_approximation,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class AgentWeight:
    """Weight configuration for an agent."""
    agent_name: str
    weight: float = 1.0
    default_weight: float = 1.0
    ema_performance: float = 0.0
    exploration_rate: float = 0.0
    exploitation_rate: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "weight": self.weight,
            "default_weight": self.default_weight,
            "ema_performance": self.ema_performance,
            "exploration_rate": self.exploration_rate,
            "exploitation_rate": self.exploitation_rate,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class TradeRecord:
    """Record of a trade with agent attribution."""
    trade_result: TradeResult
    agent_weights: Dict[str, float]
    agent_contributions: Dict[str, float]
    reward: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trade_result": self.trade_result.to_dict(),
            "agent_weights": self.agent_weights,
            "agent_contributions": self.agent_contributions,
            "reward": self.reward,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class PerformanceSummary:
    """Summary of overall system performance."""
    total_trades: int
    total_agents: int
    avg_win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    top_performing_agents: List[Dict[str, Any]]
    worst_performing_agents: List[Dict[str, Any]]
    exploration_stats: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_trades": self.total_trades,
            "total_agents": self.total_agents,
            "avg_win_rate": self.avg_win_rate,
            "total_pnl": self.total_pnl,
            "avg_pnl_per_trade": self.avg_pnl_per_trade,
            "top_performing_agents": self.top_performing_agents,
            "worst_performing_agents": self.worst_performing_agents,
            "exploration_stats": self.exploration_stats,
            "timestamp": self.timestamp.isoformat()
        }


class RLFeedbackSystem:
    """
    Reinforcement Learning Feedback System for Multi-Agent Quant Trading.
    
    This system implements reinforcement learning concepts to improve agent
    signal quality over time through feedback loops. It tracks agent performance,
    updates weights based on prediction accuracy, and uses epsilon-greedy
    exploration vs exploitation strategies.
    
    Attributes:
        ema_alpha: Exponential moving average coefficient for performance tracking
        epsilon: Base exploration rate for epsilon-greedy strategy
        epsilon_decay: Rate at which epsilon decreases over time
        epsilon_min: Minimum exploration rate
        reward_scaling: Scaling factor for reward calculation
        max_history: Maximum number of trades to keep in memory
    
    Example:
        feedback_system = RLFeedbackSystem(
            agent_names=["rsi_agent", "macd_agent", "trend_agent"],
            ema_alpha=0.3,
            epsilon=0.1
        )
        
        feedback_system.record_trade(trade_result)
        weights = feedback_system.get_agent_weights()
        feedback_system.update_agent_weights()
    """
    
    def __init__(
        self,
        agent_names: Optional[List[str]] = None,
        ema_alpha: float = 0.3,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01,
        reward_scaling: float = 1.0,
        max_history: int = 10000,
        exploration_enabled: bool = True
    ) -> None:
        """
        Initialize the RL Feedback System.
        
        Args:
            agent_names: List of agent names to track
            ema_alpha: Exponential moving average coefficient (0-1)
            epsilon: Initial exploration rate for epsilon-greedy
            epsilon_decay: Multiplicative decay factor for epsilon
            epsilon_min: Minimum exploration rate
            reward_scaling: Scaling factor for reward calculation
            max_history: Maximum number of trades to store in memory
            exploration_enabled: Whether to enable exploration
        """
        self._ema_alpha = ema_alpha
        self._epsilon = epsilon
        self._epsilon_decay = epsilon_decay
        self._epsilon_min = epsilon_min
        self._reward_scaling = reward_scaling
        self._max_history = max_history
        self._exploration_enabled = exploration_enabled
        
        self._agent_weights: Dict[str, AgentWeight] = {}
        self._agent_performance: Dict[str, AgentPerformance] = {}
        self._trade_history: Deque[TradeRecord] = deque(maxlen=max_history)
        
        self._default_weight = 1.0
        self._weight_lower_bound = 0.1
        self._weight_upper_bound = 3.0
        
        self._current_epsilon = epsilon
        self._total_updates = 0
        
        if agent_names:
            for name in agent_names:
                self._initialize_agent(name)
        
        logger.info(
            f"Initialized RLFeedbackSystem with {len(self._agent_weights)} agents, "
            f"ema_alpha={ema_alpha}, epsilon={epsilon}"
        )
    
    def _initialize_agent(self, agent_name: str) -> None:
        """Initialize tracking for a new agent."""
        self._agent_weights[agent_name] = AgentWeight(
            agent_name=agent_name,
            weight=self._default_weight,
            default_weight=self._default_weight,
            exploration_rate=0.0,
            exploitation_rate=0.0
        )
        
        self._agent_performance[agent_name] = AgentPerformance(
            agent_name=agent_name
        )
        
        logger.debug(f"Initialized tracking for agent: {agent_name}")
    
    def register_agent(self, agent_name: str) -> None:
        """
        Register a new agent with the feedback system.
        
        Args:
            agent_name: Name of the agent to register
        """
        if agent_name not in self._agent_weights:
            self._initialize_agent(agent_name)
            logger.info(f"Registered new agent: {agent_name}")
    
    def unregister_agent(self, agent_name: str) -> None:
        """
        Unregister an agent from the feedback system.
        
        Args:
            agent_name: Name of the agent to unregister
        """
        if agent_name in self._agent_weights:
            del self._agent_weights[agent_name]
            del self._agent_performance[agent_name]
            logger.info(f"Unregistered agent: {agent_name}")
    
    def record_trade(self, trade_result: TradeResult) -> None:
        """
        Record a completed trade for learning.
        
        This method processes the trade result, calculates rewards for each agent
        based on their contribution to the trade, and updates performance metrics.
        
        Args:
            trade_result: TradeResult containing trade details and outcomes
            
        Example:
            trade_result = TradeResult(
                stock_symbol="AAPL",
                entry_price=150.0,
                exit_price=155.0,
                position_size=0.1,
                pnl=500.0,
                pnl_percent=5.0,
                holding_period=5,
                decision="buy",
                agent_signals=[{"agent_name": "rsi_agent", "signal": "buy"}]
            )
            feedback_system.record_trade(trade_result)
        """
        reward = self._calculate_reward(trade_result)
        
        agent_contributions = self._attribute_trade_to_agents(
            trade_result, reward
        )
        
        trade_record = TradeRecord(
            trade_result=trade_result,
            agent_weights={
                name: w.weight for name, w in self._agent_weights.items()
            },
            agent_contributions=agent_contributions,
            reward=reward
        )
        
        self._trade_history.append(trade_record)
        
        self._update_agent_performance(trade_result, agent_contributions)
        
        if self._exploration_enabled:
            self._current_epsilon = max(
                self._epsilon_min,
                self._current_epsilon * self._epsilon_decay
            )
        
        logger.debug(
            f"Recorded trade for {trade_result.stock_symbol}: "
            f"pnl={trade_result.pnl:.2f}, reward={reward:.4f}"
        )
    
    def _calculate_reward(self, trade_result: TradeResult) -> float:
        """
        Calculate reward from trade result.
        
        Args:
            trade_result: TradeResult to calculate reward for
            
        Returns:
            Scaled reward value
        """
        sign = 1 if trade_result.pnl > 0 else -1 if trade_result.pnl < 0 else 0
        
        pnl_magnitude = abs(trade_result.pnl_percent) / 100.0
        
        reward = sign * math.sqrt(pnl_magnitude)
        
        return reward * self._reward_scaling
    
    def _attribute_trade_to_agents(
        self,
        trade_result: TradeResult,
        reward: float
    ) -> Dict[str, float]:
        """
        Attribute trade result to contributing agents.
        
        Args:
            trade_result: TradeResult containing trade details
            reward: Total reward from the trade
            
        Returns:
            Dictionary mapping agent names to their attributed reward
        """
        agent_signals = trade_result.agent_signals
        
        if not agent_signals:
            return {}
        
        contributions: Dict[str, float] = {}
        
        for signal_info in agent_signals:
            agent_name = signal_info.get("agent_name", "")
            if agent_name and agent_name in self._agent_weights:
                confidence = signal_info.get("confidence", 50.0) / 100.0
                weight = self._agent_weights[agent_name].weight
                
                contribution = (confidence * weight) / len(agent_signals)
                contributions[agent_name] = contribution
        
        total_contribution = sum(contributions.values())
        
        if total_contribution > 0:
            for agent_name in contributions:
                contributions[agent_name] = (
                    contributions[agent_name] / total_contribution
                ) * reward
        else:
            for agent_name in contributions:
                contributions[agent_name] = reward / len(contributions)
        
        return contributions
    
    def _update_agent_performance(
        self,
        trade_result: TradeResult,
        agent_contributions: Dict[str, float]
    ) -> None:
        """
        Update performance metrics for agents.
        
        Args:
            trade_result: TradeResult containing trade details
            agent_contributions: Agent attribution dictionary
        """
        is_winning = trade_result.pnl > 0
        is_losing = trade_result.pnl < 0
        
        for agent_name, contribution in agent_contributions.items():
            if agent_name not in self._agent_performance:
                self._agent_performance[agent_name] = AgentPerformance(
                    agent_name=agent_name
                )
            
            perf = self._agent_performance[agent_name]
            
            perf.total_trades += 1
            
            if is_winning:
                perf.winning_trades += 1
            elif is_losing:
                perf.losing_trades += 1
            
            perf.total_pnl += trade_result.pnl
            perf.total_pnl_percent += trade_result.pnl_percent
            
            if perf.total_trades > 0:
                perf.win_rate = perf.winning_trades / perf.total_trades
                perf.avg_pnl_per_trade = perf.total_pnl / perf.total_trades
                perf.avg_holding_period = (
                    (perf.avg_holding_period * (perf.total_trades - 1) + 
                     trade_result.holding_period) / perf.total_trades
                )
            
            perf.last_updated = datetime.now()
            
            self._update_ema_performance(agent_name, contribution)
    
    def _update_ema_performance(self, agent_name: str, contribution: float) -> None:
        """
        Update exponential moving average performance for an agent.
        
        Args:
            agent_name: Name of the agent
            contribution: Agent's contribution to the trade
        """
        weight_obj = self._agent_weights[agent_name]
        
        current_ema = weight_obj.ema_performance
        
        if current_ema == 0.0:
            weight_obj.ema_performance = contribution
        else:
            weight_obj.ema_performance = (
                self._ema_alpha * contribution +
                (1 - self._ema_alpha) * current_ema
            )
        
        weight_obj.last_updated = datetime.now()
    
    def evaluate_agent_performance(self, agent_name: str) -> AgentPerformance:
        """
        Calculate and return detailed performance metrics for an agent.
        
        Args:
            agent_name: Name of the agent to evaluate
            
        Returns:
            AgentPerformance object with detailed metrics
            
        Raises:
            KeyError: If agent_name is not registered
        """
        if agent_name not in self._agent_performance:
            raise KeyError(f"Agent '{agent_name}' not found in performance tracking")
        
        perf = self._agent_performance[agent_name]
        
        pnl_values = [
            record.trade_result.pnl 
            for record in self._trade_history
            if agent_name in record.agent_contributions
        ]
        
        if len(pnl_values) > 1:
            mean_pnl = sum(pnl_values) / len(pnl_values)
            variance = sum((x - mean_pnl) ** 2 for x in pnl_values) / len(pnl_values)
            std_dev = math.sqrt(variance)
            
            if std_dev > 0:
                perf.sharpe_approximation = mean_pnl / std_dev
            else:
                perf.sharpe_approximation = 0.0
        
        return perf
    
    def update_agent_weights(self) -> Dict[str, float]:
        """
        Adjust agent weights based on performance using exponential moving average.
        
        This method implements the core reinforcement learning weight update logic.
        Agents with positive EMA performance receive increased weights, while
        underperforming agents receive decreased weights. The update uses
        epsilon-greedy exploration to occasionally explore new weight configurations.
        
        Returns:
            Dictionary mapping agent names to their updated weights
            
        Example:
            weights = feedback_system.update_agent_weights()
            for agent, weight in weights.items():
                print(f"{agent}: {weight:.4f}")
        """
        should_explore = (
            self._exploration_enabled and 
            random.random() < self._current_epsilon
        )
        
        if should_explore:
            logger.debug(f"Exploration mode: exploring random weight adjustments")
            return self._explore()
        
        return self._exploit()
    
    def _explore(self) -> Dict[str, float]:
        """
        Exploration: Apply random weight adjustments.
        
        Returns:
            Dictionary of updated weights
        """
        updated_weights: Dict[str, float] = {}
        
        for agent_name, weight_obj in self._agent_weights.items():
            adjustment = random.uniform(-0.2, 0.2)
            new_weight = weight_obj.weight + adjustment
            
            new_weight = max(self._weight_lower_bound, min(self._weight_upper_bound, new_weight))
            
            weight_obj.weight = new_weight
            weight_obj.exploration_rate = self._current_epsilon
            weight_obj.exploitation_rate = 1.0 - self._current_epsilon
            
            updated_weights[agent_name] = new_weight
        
        self._total_updates += 1
        
        logger.info(f"Exploration update #{self._total_updates}: epsilon={self._current_epsilon:.4f}")
        
        return updated_weights
    
    def _exploit(self) -> Dict[str, float]:
        """
        Exploitation: Adjust weights based on EMA performance.
        
        Returns:
            Dictionary of updated weights
        """
        updated_weights: Dict[str, float] = {}
        
        performance_scores = []
        
        for agent_name, weight_obj in self._agent_weights.items():
            ema_perf = weight_obj.ema_performance
            
            score = ema_perf
            
            performance_scores.append((agent_name, score, weight_obj.weight))
        
        if not performance_scores:
            return {}
        
        max_score = max(abs(s[1]) for s in performance_scores)
        
        if max_score > 0:
            for agent_name, score, current_weight in performance_scores:
                normalized_score = score / max_score
                
                weight_change = normalized_score * 0.1
                
                if score >= 0:
                    new_weight = current_weight + weight_change
                else:
                    new_weight = current_weight - (weight_change * 0.5)
                
                new_weight = max(
                    self._weight_lower_bound,
                    min(self._weight_upper_bound, new_weight)
                )
                
                self._agent_weights[agent_name].weight = new_weight
                self._agent_weights[agent_name].exploration_rate = self._current_epsilon
                self._agent_weights[agent_name].exploitation_rate = 1.0 - self._current_epsilon
                
                updated_weights[agent_name] = new_weight
        
        self._total_updates += 1
        
        return updated_weights
    
    def get_agent_weights(self) -> Dict[str, float]:
        """
        Get current weights for each agent.
        
        Returns:
            Dictionary mapping agent names to their current weights
            
        Example:
            weights = feedback_system.get_agent_weights()
            print(weights)  # {'rsi_agent': 1.2, 'macd_agent': 0.8, ...}
        """
        return {
            agent_name: weight_obj.weight
            for agent_name, weight_obj in self._agent_weights.items()
        }
    
    def get_agent_weight_details(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed weight information for each agent.
        
        Returns:
            Dictionary with detailed weight information
        """
        return {
            agent_name: weight_obj.to_dict()
            for agent_name, weight_obj in self._agent_weights.items()
        }
    
    def reset_weights(self) -> None:
        """
        Reset all agent weights to default values.
        
        This resets weights to 1.0 and clears EMA performance tracking,
        but maintains trade history for future reference.
        
        Example:
            feedback_system.reset_weights()
        """
        for weight_obj in self._agent_weights.values():
            weight_obj.weight = weight_obj.default_weight
            weight_obj.ema_performance = 0.0
            weight_obj.last_updated = datetime.now()
        
        self._current_epsilon = self._epsilon
        self._total_updates = 0
        
        logger.info("Reset all agent weights to default values")
    
    def get_performance_summary(self) -> PerformanceSummary:
        """
        Get overall performance statistics across all agents.
        
        Returns:
            PerformanceSummary object with aggregated statistics
            
        Example:
            summary = feedback_system.get_performance_summary()
            print(f"Total trades: {summary.total_trades}")
            print(f"Avg win rate: {summary.avg_win_rate:.2%}")
        """
        total_trades = len(self._trade_history)
        total_pnl = sum(record.trade_result.pnl for record in self._trade_history)
        
        agent_performances = list(self._agent_performance.values())
        
        if agent_performances:
            avg_win_rate = sum(p.win_rate for p in agent_performances) / len(agent_performances)
            avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0
        else:
            avg_win_rate = 0.0
            avg_pnl_per_trade = 0.0
        
        sorted_by_pnl = sorted(
            agent_performances,
            key=lambda p: p.total_pnl,
            reverse=True
        )
        
        top_performers = [
            {"agent_name": p.agent_name, "total_pnl": p.total_pnl, "win_rate": p.win_rate}
            for p in sorted_by_pnl[:3]
        ]
        
        worst_performers = [
            {"agent_name": p.agent_name, "total_pnl": p.total_pnl, "win_rate": p.win_rate}
            for p in sorted_by_pnl[-3:] if p.total_trades > 0
        ]
        
        exploration_stats = {
            "current_epsilon": self._current_epsilon,
            "total_updates": self._total_updates,
            "exploration_enabled": self._exploration_enabled,
            "avg_exploration_rate": sum(
                w.exploration_rate for w in self._agent_weights.values()
            ) / len(self._agent_weights) if self._agent_weights else 0.0,
            "avg_exploitation_rate": sum(
                w.exploitation_rate for w in self._agent_weights.values()
            ) / len(self._agent_weights) if self._agent_weights else 0.0
        }
        
        return PerformanceSummary(
            total_trades=total_trades,
            total_agents=len(self._agent_performance),
            avg_win_rate=avg_win_rate,
            total_pnl=total_pnl,
            avg_pnl_per_trade=avg_pnl_per_trade,
            top_performing_agents=top_performers,
            worst_performing_agents=worst_performers,
            exploration_stats=exploration_stats
        )
    
    def get_trade_history(
        self,
        agent_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get trade history, optionally filtered by agent.
        
        Args:
            agent_name: Optional agent name to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of trade record dictionaries
        """
        records = list(self._trade_history)
        
        if agent_name:
            records = [
                r for r in records
                if agent_name in r.agent_contributions
            ]
        
        if limit:
            records = records[-limit:]
        
        return [r.to_dict() for r in records]
    
    def set_epsilon(self, epsilon: float) -> None:
        """
        Set the exploration rate (epsilon).
        
        Args:
            epsilon: New epsilon value (0-1)
        """
        self._epsilon = max(0.0, min(1.0, epsilon))
        self._current_epsilon = self._epsilon
        logger.info(f"Set epsilon to {self._epsilon}")
    
    def get_epsilon(self) -> float:
        """
        Get current exploration rate.
        
        Returns:
            Current epsilon value
        """
        return self._current_epsilon
    
    def set_ema_alpha(self, alpha: float) -> None:
        """
        Set the EMA alpha coefficient.
        
        Args:
            alpha: New alpha value (0-1)
        """
        self._ema_alpha = max(0.01, min(1.0, alpha))
        logger.info(f"Set EMA alpha to {self._ema_alpha}")
    
    def get_ema_alpha(self) -> float:
        """
        Get current EMA alpha coefficient.
        
        Returns:
            Current alpha value
        """
        return self._ema_alpha
    
    def enable_exploration(self) -> None:
        """Enable exploration mode."""
        self._exploration_enabled = True
        logger.info("Exploration enabled")
    
    def disable_exploration(self) -> None:
        """Disable exploration mode (pure exploitation)."""
        self._exploration_enabled = False
        self._current_epsilon = 0.0
        logger.info("Exploration disabled")
    
    def clear_history(self) -> None:
        """Clear trade history while preserving weights and performance."""
        self._trade_history.clear()
        logger.info("Cleared trade history")
    
    def get_agent_list(self) -> List[str]:
        """
        Get list of all registered agents.
        
        Returns:
            List of agent names
        """
        return list(self._agent_weights.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get complete system state as dictionary.
        
        Returns:
            Dictionary with complete system state
        """
        return {
            "config": {
                "ema_alpha": self._ema_alpha,
                "epsilon": self._epsilon,
                "epsilon_decay": self._epsilon_decay,
                "epsilon_min": self._epsilon_min,
                "reward_scaling": self._reward_scaling,
                "max_history": self._max_history,
                "exploration_enabled": self._exploration_enabled
            },
            "current_state": {
                "current_epsilon": self._current_epsilon,
                "total_updates": self._total_updates,
                "total_trades": len(self._trade_history)
            },
            "agent_weights": self.get_agent_weight_details(),
            "performance_summary": self.get_performance_summary().to_dict()
        }
    
    def __repr__(self) -> str:
        """String representation of the feedback system."""
        return (
            f"RLFeedbackSystem("
            f"agents={len(self._agent_weights)}, "
            f"trades={len(self._trade_history)}, "
            f"epsilon={self._current_epsilon:.4f})"
        )
    
    def __len__(self) -> int:
        """Get number of trades in history."""
        return len(self._trade_history)
