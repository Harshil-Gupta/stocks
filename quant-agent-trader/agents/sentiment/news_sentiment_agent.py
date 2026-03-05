from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory
from typing import Dict, Any

class NewsSentimentAgent(BaseAgent):
    def __init__(self, config=None, metadata=None):
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="News sentiment analysis",
                required_features=["news_sentiment_score", "news_count"],
                tags=["sentiment", "news"]
            )
        super().__init__(
            agent_name="news_sentiment_agent",
            agent_category=AgentCategory.SENTIMENT,
            metadata=metadata,
            config=config
        )
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        sentiment_score = features.get("news_sentiment_score", 0.0)
        news_count = features.get("news_count", 0)
        positive_headlines = features.get("positive_headlines", 0)
        negative_headlines = features.get("negative_headlines", 0)
        
        signal = "hold"
        confidence = 50.0
        numerical_score = 0.0
        reasoning = ""
        supporting_data = {}
        
        base_confidence = min(90.0, 50.0 + (news_count * 2))
        
        if sentiment_score > 0.3:
            signal = "buy"
            confidence = base_confidence
            numerical_score = min(1.0, sentiment_score)
            reasoning = (
                f"Positive news sentiment ({sentiment_score:.2f}) exceeds threshold (0.3). "
                f"News count: {news_count}, Positive headlines: {positive_headlines}, "
                f"Negative headlines: {negative_headlines}."
            )
            supporting_data = {
                "sentiment_score": sentiment_score,
                "news_count": news_count,
                "positive_headlines": positive_headlines,
                "negative_headlines": negative_headlines,
                "sentiment_condition": "positive"
            }
        elif sentiment_score < -0.3:
            signal = "sell"
            confidence = base_confidence
            numerical_score = max(-1.0, sentiment_score)
            reasoning = (
                f"Negative news sentiment ({sentiment_score:.2f}) exceeds threshold (-0.3). "
                f"News count: {news_count}, Positive headlines: {positive_headlines}, "
                f"Negative headlines: {negative_headlines}."
            )
            supporting_data = {
                "sentiment_score": sentiment_score,
                "news_count": news_count,
                "positive_headlines": positive_headlines,
                "negative_headlines": negative_headlines,
                "sentiment_condition": "negative"
            }
        else:
            signal = "hold"
            confidence = 50.0
            numerical_score = sentiment_score
            reasoning = (
                f"Neutral news sentiment ({sentiment_score:.2f}) in range [-0.3, 0.3]. "
                f"News count: {news_count}."
            )
            supporting_data = {
                "sentiment_score": sentiment_score,
                "news_count": news_count,
                "positive_headlines": positive_headlines,
                "negative_headlines": negative_headlines,
                "sentiment_condition": "neutral"
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
