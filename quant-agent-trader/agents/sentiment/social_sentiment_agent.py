"""
Social Sentiment Agent - Social media sentiment analysis.

This agent analyzes social media sentiment:
- Twitter/X sentiment
- Stock forum sentiment
- News sentiment trends
- Social media mention volume
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class SocialSentimentAgent(BaseAgent):
    """
    Agent for Social Media Sentiment analysis.
    
    Analyzes social media and forum sentiment.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the Social Sentiment agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="Social media and forum sentiment analysis for buzz and mood detection",
                required_features=["social_mentions", "social_sentiment_score", "social_trend"],
                author="Quant Team",
                tags=["social", "sentiment", "buzz", "media"]
            )
        
        super().__init__(
            agent_name="social_sentiment_agent",
            agent_category=AgentCategory.SENTIMENT,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute Social Sentiment signal.
        
        Args:
            features: Dictionary containing social sentiment data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            mentions: int = features.get("social_mentions", 0)
            sentiment: float = features.get("social_sentiment_score", 0)
            trend: float = features.get("social_trend", 0)
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if mentions > 1000 and sentiment > 0.6:
                signal = "buy"
                confidence = min(70.0, 55.0 + mentions / 100)
                numerical_score = -0.4
                reasoning = (
                    f"High social buzz ({mentions} mentions) with positive sentiment ({sentiment:.0%}). "
                    f"Strong retail interest."
                )
                supporting_data = {
                    "mentions": mentions,
                    "sentiment": sentiment,
                    "trend": trend,
                    "signal_type": "bullish_buzz"
                }
                
            elif mentions > 1000 and sentiment < -0.6:
                signal = "sell"
                confidence = min(70.0, 55.0 + mentions / 100)
                numerical_score = 0.4
                reasoning = (
                    f"High social buzz ({mentions} mentions) with negative sentiment ({sentiment:.0%}). "
                    f"Negative retail sentiment."
                )
                supporting_data = {
                    "mentions": mentions,
                    "sentiment": sentiment,
                    "trend": trend,
                    "signal_type": "bearish_buzz"
                }
                
            elif trend > 0.5 and sentiment > 0.3:
                signal = "buy"
                confidence = 60.0
                numerical_score = -0.3
                reasoning = (
                    f"Growing social interest (trend: {trend:.0%}) with positive sentiment. "
                    f"Momentum building."
                )
                supporting_data = {
                    "mentions": mentions,
                    "sentiment": sentiment,
                    "trend": trend,
                    "signal_type": "building_momentum"
                }
                
            elif trend < -0.3:
                signal = "sell"
                confidence = 55.0
                numerical_score = 0.3
                reasoning = (
                    f"Declining social interest (trend: {trend:.0%}). "
                    f"Losing attention."
                )
                supporting_data = {
                    "mentions": mentions,
                    "sentiment": sentiment,
                    "trend": trend,
                    "signal_type": "losing_attention"
                }
                
            else:
                signal = "hold"
                confidence = 50.0
                numerical_score = 0.0
                reasoning = (
                    f"Normal social activity. Mentions: {mentions}, "
                    f"Sentiment: {sentiment:.0%}."
                )
                supporting_data = {
                    "mentions": mentions,
                    "sentiment": sentiment,
                    "trend": trend,
                    "signal_type": "neutral"
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
            
        except Exception as e:
            return self._create_error_signal(f"Social Sentiment signal failed: {str(e)}")
