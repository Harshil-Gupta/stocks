"""
MFI Agent - Money Flow Index analysis.

This agent analyzes MFI to provide signals:
- MFI > 80: overbought
- MFI < 20: oversold
- MFI divergence: reversal signals
- MFI vs price: trend confirmation
"""

from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentMetadata, AgentConfig
from signals.signal_schema import AgentSignal, AgentCategory


class MFIAgent(BaseAgent):
    """
    Agent for Money Flow Index analysis.
    
    Analyzes volume-weighted RSI for momentum signals.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        metadata: Optional[AgentMetadata] = None
    ) -> None:
        """Initialize the MFI agent."""
        if metadata is None:
            metadata = AgentMetadata(
                version="1.0.0",
                description="MFI signals for volume-weighted momentum analysis",
                required_features=["mfi", "mfi_ma", "mfi_divergence", "mfi_trend"],
                author="Quant Team",
                tags=["technical", "mfi", "money_flow_index", "volume", "oscillator"]
            )
        
        super().__init__(
            agent_name="mfi_agent",
            agent_category=AgentCategory.TECHNICAL,
            metadata=metadata,
            config=config
        )
        
        self._overbought_threshold: float = 80.0
        self._oversold_threshold: float = 20.0
    
    def compute_signal(self, features: Dict[str, Any]) -> AgentSignal:
        """
        Compute MFI based trading signal.
        
        Args:
            features: Dictionary containing MFI data
            
        Returns:
            AgentSignal with trading recommendation
        """
        try:
            mfi: float = features.get("mfi", 50.0)
            mfi_ma: float = features.get("mfi_ma", 50.0)
            mfi_divergence: str = features.get("mfi_divergence", "none")
            
            signal = "hold"
            confidence: float = 50.0
            numerical_score: float = 0.0
            reasoning: str = ""
            supporting_data: Dict[str, Any] = {}
            
            if mfi > self._overbought_threshold:
                if mfi_divergence == "bearish":
                    signal = "sell"
                    confidence = 80.0
                    numerical_score = 0.5
                    reasoning = (
                        f"MFI overbought ({mfi:.1f}) with bearish divergence. "
                        f"Strong reversal signal."
                    )
                else:
                    signal = "sell"
                    confidence = 65.0
                    numerical_score = 0.4
                    reasoning = (
                        f"MFI overbought ({mfi:.1f}). "
                        f"Potential pullback."
                    )
                supporting_data = {
                    "mfi": mfi,
                    "mfi_ma": mfi_ma,
                    "mfi_divergence": mfi_divergence,
                    "zone": "overbought"
                }
                
            elif mfi < self._oversold_threshold:
                if mfi_divergence == "bullish":
                    signal = "buy"
                    confidence = 80.0
                    numerical_score = -0.5
                    reasoning = (
                        f"MFI oversold ({mfi:.1f}) with bullish divergence. "
                        f"Strong reversal signal."
                    )
                else:
                    signal = "buy"
                    confidence = 65.0
                    numerical_score = -0.4
                    reasoning = (
                        f"MFI oversold ({mfi:.1f}). "
                        f"Potential bounce."
                    )
                supporting_data = {
                    "mfi": mfi,
                    "mfi_ma": mfi_ma,
                    "mfi_divergence": mfi_divergence,
                    "zone": "oversold"
                }
                
            else:
                if mfi > mfi_ma:
                    signal = "buy"
                    confidence = 55.0
                    numerical_score = -0.2
                    reasoning = (
                        f"MFI ({mfi:.1f}) above MA. "
                        f"Positive money flow."
                    )
                    supporting_data = {
                        "mfi": mfi,
                        "mfi_ma": mfi_ma,
                        "mfi_divergence": mfi_divergence,
                        "zone": "bullish"
                    }
                else:
                    signal = "sell"
                    confidence = 55.0
                    numerical_score = 0.2
                    reasoning = (
                        f"MFI ({mfi:.1f}) below MA. "
                        f"Negative money flow."
                    )
                    supporting_data = {
                        "mfi": mfi,
                        "mfi_ma": mfi_ma,
                        "mfi_divergence": mfi_divergence,
                        "zone": "bearish"
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
            return self._create_error_signal(f"MFI signal computation failed: {str(e)}")
