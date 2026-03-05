# MULTI-AGENT STOCK INTELLIGENCE SYSTEM
## Berger Paints (BERGEPAINT) Analysis

---

## 📊 AGENT 1: FUNDAMENTAL ANALYSIS
```json
{
  "agent": "Fundamental",
  "score": 48,
  "verdict": "Bearish",
  "key_strengths": [
    "Sequential recovery: PAT +31.5% QoQ",
    "Revenue flat but stable at ₹2,984 Cr",
    "Margin expansion: 332 bps QoQ to 15.78%",
    "Market leader in paints segment"
  ],
  "key_risks": [
    "PAT declined 8.3% YoY to ₹271 Cr",
    "Volume growth muted",
    "Intense competition from Asian Paints",
    "Input cost pressures",
    "Industry growth capped at 3-5%"
  ],
  "valuation_assessment": "Trading at discount to Asian Paints but sector weak",
  "confidence": 70
}
```

## 📈 AGENT 2: TECHNICAL ANALYSIS
```json
{
  "agent": "Technical",
  "score": 38,
  "trend_direction": "Downtrend",
  "critical_levels": { "support": [420, 400], "resistance": [500, 550] },
  "verdict": "Bearish - trading below all key moving averages",
  "confidence": 70
}
```

## 🌍 AGENT 3: MACRO & SECTOR
```json
{
  "agent": "MacroSector",
  "sector_strength": "Weak - paint industry 3-5% growth ceiling",
  "external_risks": ["Competition intensifying", "Pricing pressure"],
  "verdict": "Bearish",
  "score": 40,
  "confidence": 75
}
```

## 📰 AGENT 5: SENTIMENT
```json
{
  "agent": "Sentiment",
  "media_tone": "Negative",
  "verdict": "Bearish",
  "score": 42,
  "confidence": 70
}
```

---

## 🏛 FINAL OUTPUT

```json
{
  "stock": "BERGEPAINT",
  "composite_score": 42,
  "final_decision": "SELL",
  "risk_tier": "HIGH",
  "confidence": 68
}
```

**Rationale:** Same sector issues as Asian Paints - avoid. Competition intense, growth muted.
