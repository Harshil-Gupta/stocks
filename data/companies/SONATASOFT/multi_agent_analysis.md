# MULTI-AGENT STOCK INTELLIGENCE SYSTEM
## SONATA SOFTWARE (SONATSOFTW) Analysis

---

# 📊 AGENT 1: FUNDAMENTAL ANALYSIS AGENT

```json
{
  "agent": "Fundamental",
  "score": 72,
  "verdict": "Bullish",
  "key_strengths": [
    "Revenue growth: +45.4% QoQ, +8.36% YoY",
    "EBITDA margin expansion: 16.6% → 19.5% in 3 quarters",
    "Strong ROCE: 30.13%",
    "AI order book growing: 8% → 14% in 3 quarters",
    "Utilization at record 90%",
    "Zero debt, clean balance sheet",
    "Stable promoter holding at 28.17%",
    "Consistent dividend policy"
  ],
  "key_risks": [
    "International revenue growth stagnant: +0.3% QoQ",
    "Client concentration: Top 10 = 53% revenue",
    "FII selling: 12.29% → 8.79% in 1 year",
    "Domestic business volatility due to Microsoft strategy change"
  ],
  "valuation_assessment": "Fair value. Forward PE ~16.5x is reasonable for IT services with AI transformation story. Trading at discount to sector average.",
  "financial_health_summary": "Strong. Margin expansion is structural (utilization, offshoring, AI productivity), not one-off. Cash position healthy despite reduction from ₹600cr to ₹323cr (dividend payments).",
  "confidence": 80
}
```

---

# 📈 AGENT 2: TECHNICAL ANALYSIS AGENT

```json
{
  "agent": "Technical",
  "score": 35,
  "trend_direction": "Strong Downtrend",
  "momentum_assessment": "Oversold with bearish momentum. All moving averages trending down. RSI at 28.19 indicates oversold but can stay oversold.",
  "critical_levels": {
    "support": [253.20, 246.15, 240.05],
    "resistance": [266.35, 272.45, 279.50]
  },
  "volatility_profile": "Very High. Stock made new 52-week low. Beta likely elevated.",
  "verdict": "Bearish - Downtrend intact but approaching strong support",
  "confidence": 70
}
```

**Technical Notes:**
- Price below all SMAs (20, 50, 100, 200)
- RSI at 28.19 (oversold territory)
- MACD bearish crossover
- Strong downtrend - lower highs and lower lows
- Could see bounce from support levels but trend is down

---

# 🌍 AGENT 3: MACRO & SECTOR AGENT

```json
{
  "agent": "MacroSector",
  "macro_environment": "Favorable. RBI repo rate at 5.25% (cut 25bps in Dec 2025). Inflation low at 1.33%. GDP growth strong at 8.2%. Rupee stable.",
  "sector_strength": "Moderate. India IT sector to grow 6.1% to $315bn in FY26 (Nasscom). Sector facing AI disruption concerns but fundamentals intact.",
  "external_risks": [
    "AI disruption fears causing sector-wide derating",
    "Geopolitical uncertainty",
    "Global IT spending moderation"
  ],
  "tailwinds": [
    "IT exports expected at $246bn (+5.6% YoY)",
    "GCC (Global Capability Centres) expansion in India",
    "AI services demand rising",
    "Budget 2026 increased safe harbour threshold to Rs 2000cr",
    "Digital transformation spending continues"
  ],
  "verdict": "Neutral to Positive",
  "score": 60,
  "confidence": 75
}
```

---

# 🤖 AGENT 4: QUANT & STATISTICAL AGENT

```json
{
  "agent": "Quant",
  "volatility_score": 85,
  "risk_metrics": {
    "beta": "Elevated (likely 1.3-1.5 based on volatility)",
    "52_week_range": "270.05 - 464.20",
    "drawdown_from_high": "-45%",
    "avg_daily_range": "High volatility"
  },
  "statistical_bias": "Bearish - strong momentum down, approaching support but no reversal signal",
  "probabilistic_outlook": "60% probability of further downside to 240, 40% probability of bounce to 280",
  "verdict": "Cautious - High volatility, unclear direction from current levels",
  "confidence": 55
}
```

---

# 📰 AGENT 5: SENTIMENT & NEWS AGENT

```json
{
  "agent": "Sentiment",
  "media_tone": "Mixed. Recent Microsoft Frontier Partner recognition positive but overshadowed by broader sector concerns.",
  "institutional_behavior": "Bearish. FII selling continues (down to 8.79%). MF holding stable at 25.6%.",
  "analyst_trend": "Mixed. ICICI Direct downgraded to HOLD (₹350), IDBI Capital upgraded to BUY (₹355).",
  "retail_sentiment": "Negative. Stock at new 52-week low. Extreme fear visible.",
  "event_risk": "Low. No major corporate events pending.",
  "verdict": "Bearish - Sentiment at extreme negative, potential contrarian opportunity",
  "score": 45,
  "confidence": 70
}
```

---

# 🧩 MASTER AGENT SYNTHESIS

## Weighting Applied:
- Fundamental: 30%
- Technical: 20%
- Macro/Sector: 15%
- Quant: 20%
- Sentiment: 15%

## Score Calculation:
| Agent | Score | Weight | Weighted |
|-------|-------|--------|----------|
| Fundamental | 72 | 30% | 21.6 |
| Technical | 35 | 20% | 7.0 |
| Macro/Sector | 60 | 15% | 9.0 |
| Quant | 45 | 20% | 9.0 |
| Sentiment | 45 | 15% | 6.75 |
| **TOTAL** | | | **53.35** |

---

# 🏛 FINAL MASTER OUTPUT

```json
{
  "stock": "SONATSOFTW",
  "composite_score": 53,
  "final_decision": "HOLD",
  "risk_tier": "MEDIUM",
  "confidence": 68,
  "contradictions_detected": [
    "Fundamental: Bullish (72) vs Technical: Bearish (35) - Strong conflict",
    "Fundamental shows margin expansion, AI momentum while technical shows downtrend",
    "Sentiment extreme negative (contrarian opportunity) vs price downtrend"
  ],
  "primary_drivers": [
    "AI order book growth (8% → 14%) - structural change",
    "Margin expansion trajectory (16.6% → 19.5%)",
    "Microsoft Frontier Partner status - differentiation",
    "Large deal pipeline strength (40% of pipeline)"
  ],
  "key_risks": [
    "FII selling pressure continues",
    "Client concentration (top 10 = 53%)",
    "International revenue stagnant",
    "Technical downtrend intact"
  ],
  "strategic_positioning": {
    "short_term": "Hold - wait for technical stabilization above 280",
    "long_term": "Accumulate on dips - fundamental story compelling",
    "ideal_investor_type": "Medium to long-term investor with 6-12 month horizon"
  }
}
```

---

## 📋 DECISION MATRIX

| Score Range | Decision |
|-------------|----------|
| 85–100 | STRONG BUY |
| 70–84 | BUY |
| 50–69 | **HOLD** |
| 30–49 | SELL |
| <30 | STRONG SELL |

**Result: HOLD (Score: 53)**

---

## 🎯 SUMMARY

**SONATA SOFTWARE** presents a classic **fundamental vs technical conflict**:

- **Bull Case:** AI transformation real (14% order book), margins expanding structurally, Microsoft differentiation, trading at reasonable valuations
- **Bear Case:** Technical downtrend severe (new 52W low), FII selling, client concentration risks

**Recommendation:** HOLD and watch. If technical stabilization occurs (price holds above 260-270), would upgrade to BUY. Current level is attractive for long-term value but risky for short-term trades.

**Key Catalyst to Watch:** Q4 FY26 results - if large BFSI deals convert and AI order book grows, could trigger re-rating.
