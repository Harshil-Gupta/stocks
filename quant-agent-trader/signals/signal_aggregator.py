"""
Signal Aggregator Engine - Multi-agent signal aggregation system.
Aggregates signals from multiple agents using weighted ensemble logic
with regime-based weight adjustments and explainability.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from signals.signal_schema import (
    AgentSignal,
    AggregatedSignal,
    SignalType,
    VALID_SIGNALS,
)
from config.settings import REGIME_WEIGHTS, config


SIGNAL_SCORE_MAP = {
    "strong_buy": 1.0,
    "buy": 0.5,
    "hold": 0.0,
    "sell": -0.5,
    "strong_sell": -1.0,
}

REVERSE_SCORE_MAP = {
    1.0: "strong_buy",
    0.5: "buy",
    0.0: "hold",
    -0.5: "sell",
    -1.0: "strong_sell",
}


@dataclass
class SignalExplanation:
    """Explanation for an aggregated signal decision."""

    decision: str
    confidence: float
    supporting_signals: List[Dict]
    conflicting_signals: List[Dict]
    category_breakdown: Dict[str, Dict]
    reasoning: str


@dataclass
class WeightConfig:
    """Configuration for signal weights."""

    weights: Dict[str, float]
    regime: str = "normal"


class SignalAggregator:
    """
    Aggregates signals from multiple agents using weighted ensemble logic.

    Supports regime-based weight adjustments to adapt to different market
    conditions (bull, bear, sideways, high_volatility).

    Outputs 5-class signals: strong_buy, buy, hold, sell, strong_sell
    """

    DEFAULT_WEIGHTS = {
        "technical": 0.30,
        "fundamental": 0.25,
        "sentiment": 0.15,
        "macro": 0.10,
        "market_structure": 0.10,
        "risk": 0.10,
    }

    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """
        Initialize the SignalAggregator.

        Args:
            custom_weights: Optional custom weights to override defaults.
        """
        self.base_weights = custom_weights or self.DEFAULT_WEIGHTS
        self._validate_weights(self.base_weights)

    def _validate_weights(self, weights: Dict[str, float]) -> None:
        """Validate that weights sum to 1.0 and contain all required categories."""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        required_categories = {
            "technical",
            "fundamental",
            "sentiment",
            "macro",
            "market_structure",
            "risk",
        }
        missing = required_categories - set(weights.keys())
        if missing:
            raise ValueError(f"Missing weight categories: {missing}")

    def _get_signal_score(self, signal_str: str) -> float:
        """Get numerical score for a signal string."""
        return SIGNAL_SCORE_MAP.get(signal_str.lower(), 0.0)

    def _score_to_signal(self, score: float) -> str:
        """Convert numerical score to 5-class signal.

        Thresholds (0-100 scale, normalized from -1 to 1):
        - >= 85: STRONG_BUY
        - 60 to 85: BUY
        - 40 to 60: HOLD
        - 25 to 40: SELL
        - < 25: STRONG_SELL

        Boundary values (like 25, 40, 60, 85) choose lower signal.
        """
        # Normalize score from [-1, 1] to [0, 100]
        normalized = (score + 1) * 50

        if normalized >= 85:
            return "strong_buy"
        elif normalized >= 60:
            return "buy"
        elif normalized >= 40:
            return "hold"
        elif normalized >= 25:
            return "sell"
        else:
            return "strong_sell"

    def _score_to_signal_direct(self, score: float) -> str:
        """Convert numerical score (0-100) directly to 5-class signal.

        Thresholds:
        - >= 85: STRONG_BUY
        - 60 to 85: BUY
        - 40 to 60: HOLD
        - 25 to 40: SELL
        - < 25: STRONG_SELL

        Boundary values (like 25, 40, 60, 85) choose lower signal.
        """
        if score >= 85:
            return "strong_buy"
        elif score >= 60:
            return "buy"
        elif score >= 40:
            return "hold"
        elif score >= 25:
            return "sell"
        else:
            return "strong_sell"

    def aggregate_signals(
        self,
        signals: List[AgentSignal],
        regime: str = "normal",
        stock_symbol: str = "UNKNOWN",
    ) -> AggregatedSignal:
        """
        Aggregate multiple agent signals into a single decision.

        Args:
            signals: List of AgentSignal objects from different agents.
            regime: Market regime for weight adjustment (normal, bull, bear,
                   sideways, high_volatility).
            stock_symbol: Stock ticker symbol.

        Returns:
            AggregatedSignal with final_score, decision, confidence, and
            supporting/conflicting agent lists.
        """
        if not signals:
            return self._create_empty_aggregated_signal(stock_symbol, regime)

        weights = self._get_regime_weights(regime)
        weighted_score = self._apply_weights(signals, weights)

        decision = self._score_to_signal(weighted_score)

        consensus = self._detect_consensus(signals)

        confidence = self._calculate_confidence(signals, consensus)

        supporting_agents = consensus["supporting"]
        conflicting_agents = consensus["conflicting"]

        return AggregatedSignal(
            stock_symbol=stock_symbol,
            final_score=weighted_score,
            decision=decision,
            confidence=confidence,
            supporting_agents=supporting_agents,
            conflicting_agents=conflicting_agents,
            agent_signals=signals,
            regime=regime,
            timestamp=datetime.now(),
        )

    def _get_regime_weights(self, regime: str) -> Dict[str, float]:
        """
        Get weight configuration based on market regime.

        Args:
            regime: Market regime type.

        Returns:
            Dictionary of category weights for the regime.
        """
        regime_normalized = regime.lower().replace(" ", "_").replace("-", "_")

        if regime_normalized in REGIME_WEIGHTS:
            regime_weights = REGIME_WEIGHTS[regime_normalized]
            self._validate_weights(regime_weights)
            return regime_weights

        return self.base_weights.copy()

    def _apply_weights(
        self, signals: List[AgentSignal], weights: Dict[str, float]
    ) -> float:
        """
        Apply weighted ensemble to signals.

        Args:
            signals: List of AgentSignal objects.
            weights: Dictionary mapping category to weight.

        Returns:
            Weighted score in range [-1, 1].
        """
        if not signals:
            return 0.0

        category_scores: Dict[str, List[float]] = {}

        for signal in signals:
            category = signal.agent_category
            if category not in category_scores:
                category_scores[category] = []

            numerical = self._get_signal_score(signal.signal)
            confidence_factor = signal.confidence / 100.0
            weighted_signal = numerical * (confidence_factor**0.5)
            category_scores[category].append(weighted_signal)

        weighted_sum = 0.0
        total_weight_used = 0.0

        for category, score_list in category_scores.items():
            if score_list:
                avg_score = sum(score_list) / len(score_list)
                weight = weights.get(category, 0.0)
                weighted_sum += avg_score * weight
                total_weight_used += weight

        if total_weight_used > 0:
            normalized_weighted = weighted_sum / total_weight_used
        else:
            normalized_weighted = 0.0

        buy_signals = sum(1 for s in signals if self._get_signal_score(s.signal) > 0.1)
        sell_signals = sum(
            1 for s in signals if self._get_signal_score(s.signal) < -0.1
        )
        strong_buy = sum(1 for s in signals if s.signal == "strong_buy")
        strong_sell = sum(1 for s in signals if s.signal == "strong_sell")

        if strong_buy > strong_sell:
            normalized_weighted += 0.1
        elif strong_sell > strong_buy:
            normalized_weighted -= 0.1
        elif buy_signals > sell_signals:
            normalized_weighted += 0.025
        elif sell_signals > buy_signals:
            normalized_weighted -= 0.025

        return normalized_weighted

    def _detect_consensus(self, signals: List[AgentSignal]) -> Dict[str, List[str]]:
        """
        Detect consensus and conflicts among agent signals.

        Args:
            signals: List of AgentSignal objects.

        Returns:
            Dictionary with 'supporting' and 'conflicting' agent lists.
            Supporting agents align with the majority decision.
            Conflicting agents disagree with the majority.
        """
        if not signals:
            return {"supporting": [], "conflicting": []}

        signal_counts: Dict[str, int] = {}
        for signal in signals:
            signal_type = signal.signal.lower()
            signal_counts[signal_type] = signal_counts.get(signal_type, 0) + 1

        max_count = max(signal_counts.values())
        majority_signals = [s for s, c in signal_counts.items() if c == max_count]

        if len(majority_signals) == 1:
            majority = majority_signals[0]
        else:
            majority = "hold" if "hold" in majority_signals else majority_signals[0]

        supporting = []
        conflicting = []

        for signal in signals:
            if signal.signal.lower() == majority:
                supporting.append(signal.agent_name)
            else:
                conflicting.append(signal.agent_name)

        return {"supporting": supporting, "conflicting": conflicting}

    def _calculate_confidence(
        self, signals: List[AgentSignal], consensus: Dict[str, List[str]]
    ) -> float:
        """
        Calculate confidence score for aggregated signal.

        Args:
            signals: List of AgentSignal objects.
            consensus: Consensus detection result.

        Returns:
            Confidence score in range [0, 100].
        """
        if not signals:
            return 0.0

        supporting_count = len(consensus["supporting"])
        conflicting_count = len(consensus["conflicting"])
        total_agents = len(signals)

        if total_agents == 0:
            return 0.0

        consensus_ratio = supporting_count / total_agents if total_agents > 0 else 0.0

        avg_confidence = sum(s.confidence for s in signals) / total_agents

        confidence_spread = self._calculate_confidence_spread(signals)

        confidence = (
            (consensus_ratio * 50)
            + (avg_confidence * 0.35)
            + (confidence_spread * 0.15)
        )

        return min(100.0, max(0.0, confidence))

    def _calculate_confidence_spread(self, signals: List[AgentSignal]) -> float:
        """
        Calculate confidence based on how clustered the signals are.

        Args:
            signals: List of AgentSignal objects.

        Returns:
            Spread score in range [0, 100].
        """
        if len(signals) <= 1:
            return 50.0

        numerical_scores = [self._get_signal_score(s.signal) for s in signals]

        mean_score = sum(numerical_scores) / len(numerical_scores)

        variance = sum((x - mean_score) ** 2 for x in numerical_scores) / len(
            numerical_scores
        )
        std_dev = variance**0.5

        spread_factor = max(0, 1 - std_dev)

        return spread_factor * 100

    def _normalize_score(self, score: float) -> float:
        """
        Normalize score to [-1, 1] range.

        Args:
            score: Score in any range.

        Returns:
            Score clamped to [-1, 1].
        """
        return max(-1.0, min(1.0, score))

    def _score_to_decision(self, final_score: float) -> str:
        """
        Convert numerical score to 5-class trading decision.

        Args:
            final_score: Score in range [-1, 1].

        Returns:
            5-class trading decision: 'strong_buy', 'buy', 'hold', 'sell', or 'strong_sell'

        Thresholds (normalized to 0-100):
        - STRONG_BUY: >= 85
        - BUY: 60-85
        - HOLD: 40-60
        - SELL: 25-40
        - STRONG_SELL: < 25
        """
        return self._score_to_signal(final_score)

    def _create_empty_aggregated_signal(
        self, stock_symbol: str, regime: str
    ) -> AggregatedSignal:
        """Create an empty aggregated signal when no signals are provided."""
        return AggregatedSignal(
            stock_symbol=stock_symbol,
            final_score=0.0,
            decision="hold",
            confidence=0.0,
            supporting_agents=[],
            conflicting_agents=[],
            agent_signals=[],
            regime=regime,
            timestamp=datetime.now(),
        )

    def get_weight_breakdown(
        self, signals: List[AgentSignal], regime: str = "normal"
    ) -> Dict[str, Dict[str, float]]:
        """
        Get detailed weight breakdown by category.

        Args:
            signals: List of AgentSignal objects.
            regime: Market regime for weight adjustment.

        Returns:
            Dictionary showing contribution from each category.
        """
        weights = self._get_regime_weights(regime)

        breakdown: Dict[str, Dict[str, float]] = {}

        for signal in signals:
            category = signal.agent_category
            if category not in breakdown:
                breakdown[category] = {
                    "weight": weights.get(category, 0.0),
                    "avg_score": 0.0,
                    "agent_count": 0,
                    "contribution": 0.0,
                }

            breakdown[category]["agent_count"] += 1
            breakdown[category]["avg_score"] += self._get_signal_score(signal.signal)

        for category in breakdown:
            count = breakdown[category]["agent_count"]
            if count > 0:
                breakdown[category]["avg_score"] /= count
                breakdown[category]["contribution"] = (
                    breakdown[category]["avg_score"] * breakdown[category]["weight"]
                )

        return breakdown

    def explain(
        self,
        signals: List[AgentSignal],
        regime: str = "sideways",
        stock_symbol: str = "UNKNOWN",
    ) -> SignalExplanation:
        """
        Generate detailed explanation for signal decision.

        Args:
            signals: List of agent signals
            regime: Current market regime
            stock_symbol: Stock symbol

        Returns:
            SignalExplanation with detailed reasoning
        """
        if not signals:
            return SignalExplanation(
                decision="hold",
                confidence=0.0,
                supporting_signals=[],
                conflicting_signals=[],
                category_breakdown={},
                reasoning="No signals provided",
            )

        weights = self._get_regime_weights(regime)
        breakdown = self.get_weight_breakdown(signals, regime)

        supporting = []
        conflicting = []

        for signal in signals:
            signal_info = {
                "agent": signal.agent_name,
                "category": signal.agent_category,
                "signal": signal.signal,
                "confidence": signal.confidence,
                "score": self._get_signal_score(signal.signal),
                "reasoning": signal.reasoning,
            }

            if signal.is_buy:
                supporting.append(signal_info)
            elif signal.is_sell:
                conflicting.append(signal_info)

        decision = self._score_to_decision(
            self._normalize_score(self._apply_weights(signals, weights))
        )

        consensus = self._detect_consensus(signals)
        confidence = self._calculate_confidence(signals, consensus)

        reasoning = self._generate_reasoning(
            decision=decision,
            supporting=supporting,
            conflicting=conflicting,
            breakdown=breakdown,
            regime=regime,
        )

        return SignalExplanation(
            decision=decision,
            confidence=confidence,
            supporting_signals=supporting,
            conflicting_signals=conflicting,
            category_breakdown=breakdown,
            reasoning=reasoning,
        )

    def _generate_reasoning(
        self,
        decision: str,
        supporting: List[Dict],
        conflicting: List[Dict],
        breakdown: Dict,
        regime: str,
    ) -> str:
        """Generate human-readable reasoning."""
        reasons = []

        if decision in ("strong_buy", "buy"):
            if supporting:
                top_signals = sorted(
                    supporting, key=lambda x: x["confidence"], reverse=True
                )[:3]
                names = [s["agent"].replace("_agent", "") for s in top_signals]
                reasons.append(f"Buy signals from: {', '.join(names)}")

            if breakdown:
                top_cats = sorted(
                    breakdown.items(),
                    key=lambda x: x[1].get("contribution", 0),
                    reverse=True,
                )[:2]
                cat_names = [c[0] for c in top_cats]
                reasons.append(f"Strong categories: {', '.join(cat_names)}")

            if decision == "strong_buy":
                reasons.append("Strong momentum indicating high conviction")

        elif decision in ("strong_sell", "sell"):
            if conflicting:
                top_signals = sorted(
                    conflicting, key=lambda x: x["confidence"], reverse=True
                )[:3]
                names = [s["agent"].replace("_agent", "") for s in top_signals]
                reasons.append(f"Sell signals from: {', '.join(names)}")

            if decision == "strong_sell":
                reasons.append("Strong bearish momentum indicating high conviction")

        else:
            reasons.append("Mixed signals from agents")
            if breakdown:
                reasons.append(f"No clear consensus in: {', '.join(breakdown.keys())}")

        if regime != "sideways":
            reasons.append(f"Market regime: {regime}")

        return ". ".join(reasons)


def aggregate_signals(
    signals: List[AgentSignal],
    regime: str = "normal",
    stock_symbol: str = "UNKNOWN",
    custom_weights: Optional[Dict[str, float]] = None,
) -> AggregatedSignal:
    """
    Convenience function to aggregate signals.

    Args:
        signals: List of AgentSignal objects.
        regime: Market regime for weight adjustment.
        stock_symbol: Stock ticker symbol.
        custom_weights: Optional custom weights.

    Returns:
        AggregatedSignal with final decision.
    """
    aggregator = SignalAggregator(custom_weights=custom_weights)
    return aggregator.aggregate_signals(signals, regime, stock_symbol)
