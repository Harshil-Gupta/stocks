from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from typing import Dict, Any

class AnalystRatingAgent(BaseAgent):
    def __init__(self, config=None, metadata=None):
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Analyst consensus rating analysis",
                required_features=["analyst_consensus", "buy_count", "hold_count", "sell_count"],
                tags=["sentiment", "analyst", "ratings"]
            )
        super().__init__(
            agent_name="analyst_rating_agent",
            agent_category=AgentCategory.SENTIMENT,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        consensus = features.get("analyst_consensus", 3.0)
        buy_count = features.get("buy_count", 0)
        hold_count = features.get("hold_count", 0)
        sell_count = features.get("sell_count", 0)
        recent_changes = features.get("recent_rating_changes", 0)
        
        signal = "hold"
        confidence = 50.0
        numerical_score = 0.0
        reasoning = ""
        supporting_data = {}
        
        total_analysts = buy_count + hold_count + sell_count
        base_confidence = min(90.0, 50.0 + (total_analysts * 2)) if total_analysts > 0 else 50.0
        
        more_buys_than_sells = buy_count > sell_count
        more_sells_than_buys = sell_count > buy_count
        
        if consensus >= 4.0 and more_buys_than_sells:
            signal = "buy"
            confidence = base_confidence
            numerical_score = min(1.0, (consensus - 3) / 2)
            reasoning = (
                f"Strong analyst consensus at {consensus:.1f}/5 with {buy_count} buys vs {sell_count} sells. "
                f"Total analyst coverage: {total_analysts}. Recent rating changes: {recent_changes}."
            )
            supporting_data = {
                "consensus": consensus,
                "buy_count": buy_count,
                "hold_count": hold_count,
                "sell_count": sell_count,
                "total_analysts": total_analysts,
                "recent_changes": recent_changes,
                "rating_condition": "strong_buy"
            }
        elif consensus <= 2.0 and more_sells_than_buys:
            signal = "sell"
            confidence = base_confidence
            numerical_score = max(-1.0, -(3 - consensus) / 2)
            reasoning = (
                f"Weak analyst consensus at {consensus:.1f}/5 with {sell_count} sells vs {buy_count} buys. "
                f"Total analyst coverage: {total_analysts}. Recent rating changes: {recent_changes}."
            )
            supporting_data = {
                "consensus": consensus,
                "buy_count": buy_count,
                "hold_count": hold_count,
                "sell_count": sell_count,
                "total_analysts": total_analysts,
                "recent_changes": recent_changes,
                "rating_condition": "strong_sell"
            }
        elif consensus >= 4.0:
            signal = "hold"
            confidence = base_confidence - 10
            numerical_score = 0.3
            reasoning = (
                f"Positive analyst consensus at {consensus:.1f}/5 but mixed signals. "
                f"Buy: {buy_count}, Hold: {hold_count}, Sell: {sell_count}. "
                f"Total analyst coverage: {total_analysts}."
            )
            supporting_data = {
                "consensus": consensus,
                "buy_count": buy_count,
                "hold_count": hold_count,
                "sell_count": sell_count,
                "total_analysts": total_analysts,
                "recent_changes": recent_changes,
                "rating_condition": "positive_mixed"
            }
        elif consensus <= 2.0:
            signal = "hold"
            confidence = base_confidence - 10
            numerical_score = -0.3
            reasoning = (
                f"Negative analyst consensus at {consensus:.1f}/5 but mixed signals. "
                f"Buy: {buy_count}, Hold: {hold_count}, Sell: {sell_count}. "
                f"Total analyst coverage: {total_analysts}."
            )
            supporting_data = {
                "consensus": consensus,
                "buy_count": buy_count,
                "hold_count": hold_count,
                "sell_count": sell_count,
                "total_analysts": total_analysts,
                "recent_changes": recent_changes,
                "rating_condition": "negative_mixed"
            }
        else:
            signal = "hold"
            confidence = 50.0
            numerical_score = (consensus - 3) / 2
            reasoning = (
                f"Neutral analyst consensus at {consensus:.1f}/5 in range [2.5, 4]. "
                f"Buy: {buy_count}, Hold: {hold_count}, Sell: {sell_count}. "
                f"Total analyst coverage: {total_analysts}."
            )
            supporting_data = {
                "consensus": consensus,
                "buy_count": buy_count,
                "hold_count": hold_count,
                "sell_count": sell_count,
                "total_analysts": total_analysts,
                "recent_changes": recent_changes,
                "rating_condition": "neutral"
            }
        
        return AgentSignal(
            agent_name=self._agent_name,
            agent_category=self._agent_category.value,
            signal=signal,
            confidence=confidence,
            numerical_score=numerical_score,
            reasoning=reasoning,
            supporting_data=supporting_data
        )
