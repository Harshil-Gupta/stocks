---
name: mf-analyser
description: >
  Analyses Indian mutual funds the way a fee-only advisor would — rolling returns, alpha vs
  benchmark, expense ratio value, fund manager track record, portfolio concentration, and
  whether the fund is genuinely earning its fee or just hugging the index. Use when user asks
  "analyse this mutual fund", "is [fund name] worth holding", "compare these two funds",
  "should I stay in [fund]", "review my SIPs", or mentions any mutual fund by name or AMFI code.
  Fetches live NAV and holdings data from mfapi.in and fund factsheets. Outputs a Fund Report
  Card with a Keep / Review / Replace verdict.
---

# MF Analyser — Mutual Fund Due Diligence

Evaluate a mutual fund the way a fee-only advisor would: not just trailing returns,
but rolling returns, genuine alpha, manager consistency, and whether you're getting
what you're paying for.

## Data Sources

**NAV & scheme data (free, no auth required):**
- Search: `https://api.mfapi.in/mf/search?q={FUND_NAME}`
- Historical NAV: `https://api.mfapi.in/mf/{SCHEME_CODE}`
- Latest NAV: `https://api.mfapi.in/mf/{SCHEME_CODE}/latest`

**Holdings & factsheet:**
- WebFetch the AMC's own factsheet page (monthly, published by SEBI mandate)
- WebSearch `"{FUND_NAME}" factsheet {CURRENT_MONTH} {CURRENT_YEAR} filetype:pdf`
- ValueResearch: WebFetch `https://www.valueresearchonline.com/funds/` (for ratings + alpha data)

**Benchmark returns:**
- WebSearch `"{BENCHMARK_INDEX}" returns 1Y 3Y 5Y` (e.g., "Nifty 50 TRI returns")

---

## Workflow

### Step 1: Identify the fund

Extract fund name or AMFI code from user input.
- If name given: GET `https://api.mfapi.in/mf/search?q={FUND_NAME}` → get scheme_code
- If AMFI code given: use directly
- If ambiguous (e.g., "Parag Parikh Flexi Cap") — confirm Direct vs Regular plan. **Always prefer Direct plan** for analysis unless user specifies Regular.

### Step 2: Fetch NAV history

GET `https://api.mfapi.in/mf/{SCHEME_CODE}` — returns full NAV history as JSON array `[{date, nav}]`.

Parse and build a time series. You'll need at least 5 years of data for meaningful rolling return analysis.

### Step 3: Fetch fund factsheet and holdings

WebSearch for the latest monthly factsheet PDF from the AMC. Extract:
- Top 10 holdings with % weight
- Sector allocation
- Number of stocks
- AUM
- Expense ratio (TER)
- Fund manager name and tenure in this fund
- Portfolio P/E, P/B (if disclosed)
- Benchmark index name

### Step 4: Compute returns — rolling, not trailing

**Why rolling returns matter more than trailing:**
Trailing returns are a snapshot. If you check on a peak day, a bad fund looks great.
Rolling returns show consistency — how often has this fund delivered over any given period.

**Compute these from NAV history:**

**1-year rolling returns** (compute for every starting day in the last 3 years):
- What % of 1Y periods gave >12% return?
- What % of 1Y periods gave negative return?

**3-year rolling returns** (compute for every starting day in the last 5 years):
- What % of 3Y periods beat the benchmark?
- What is the median 3Y CAGR?

**SIP returns (XIRR simulation):**
- Simulate a monthly SIP of ₹10,000 from 3 years ago to today
- Compute XIRR — this is what a real SIP investor actually earned

**Implementation (Python via bash):**
```bash
python3 << 'EOF'
import json, math
from datetime import datetime, timedelta

# Load NAV data (pass as JSON string)
nav_data = json.loads("""PASTE_NAV_JSON_HERE""")

# Parse dates and NAVs
records = [(datetime.strptime(r['date'], '%d-%m-%Y'), float(r['nav'])) 
           for r in nav_data['data']]
records.sort(key=lambda x: x[0])

# 1-year rolling returns
results_1y = []
for i, (d1, n1) in enumerate(records):
    target = d1 + timedelta(days=365)
    for d2, n2 in records[i:]:
        if d2 >= target:
            ret = (n2/n1 - 1) * 100
            results_1y.append(ret)
            break

positive_pct = sum(1 for r in results_1y if r > 0) / len(results_1y) * 100
beat_12_pct = sum(1 for r in results_1y if r > 12) / len(results_1y) * 100
negative_pct = sum(1 for r in results_1y if r < 0) / len(results_1y) * 100
median_1y = sorted(results_1y)[len(results_1y)//2]

print(f"1Y Rolling: median={median_1y:.1f}%, beat 12%: {beat_12_pct:.0f}% of periods, negative: {negative_pct:.0f}% of periods")

# Trailing returns
def trailing(years):
    target = records[-1][0] - timedelta(days=int(years*365))
    for d, n in records:
        if d >= target:
            return ((records[-1][1]/n) ** (1/years) - 1) * 100
    return None

print(f"Trailing: 1Y={trailing(1):.1f}%, 3Y={trailing(3):.1f}%, 5Y={trailing(5):.1f}%")
EOF
```

### Step 5: Alpha calculation

Alpha = Fund CAGR − Benchmark CAGR (same period, same start/end dates)

Compute for 1Y, 3Y, 5Y.

**Interpret:**
- Alpha >3% consistently: Fund manager genuinely adding value
- Alpha 0–3%: Marginal value add, check if expense ratio consumes the alpha
- Alpha <0%: Underperforming index; unless there's a strong thesis for holding, replace with index fund

**Expense ratio vs alpha:**
- Net alpha = Gross alpha − TER
- If TER is 1.5% but gross alpha is 1.2%, net alpha is negative → index fund wins

### Step 6: Fund manager assessment

From factsheet, extract manager name and tenure. Then:

WebSearch `"{FUND_MANAGER_NAME}" {FUND_NAME} track record performance`

Look for:
- How long has this manager run this specific fund?
- Any funds previously managed — did those perform well under them?
- Any recent manager change? (Flag: returns attributed to current manager may be from predecessor)
- Manager also runs how many other funds? (>5 funds = attention dilution risk)

**Red flags:**
- Manager tenure <2 years in this fund (can't attribute track record to them)
- Manager change in the last 12 months (past performance not comparable)
- Same manager runs 8+ funds simultaneously

### Step 7: Portfolio quality assessment

From factsheet holdings:
- **Concentration:** Top 10 holdings % of portfolio. >60% = concentrated bet, not truly diversified
- **Stock count:** <20 stocks = high conviction fund (higher volatility, needs strong manager). >60 stocks = closet index fund
- **Sector tilt:** Any sector >30%? That's a sector bet hiding inside a diversified fund mandate
- **Overlap with Nifty 50:** If top holdings are all Nifty 50 names with similar weights, this is a closet index fund charging active fees

**Closet indexer test:**
If fund's top 10 holdings overlap >70% with benchmark's top 10, and alpha <2%, it's a closet indexer. Replace with direct index fund at 0.1% TER.

### Step 8: Risk-adjusted returns

Compute (from NAV history):

**Max drawdown:** Largest peak-to-trough NAV decline in last 5 years — shows downside risk
**Recovery time:** How many months to recover from the largest drawdown?

**Interpret:**
- Max drawdown <30% for equity fund: reasonable
- Max drawdown >40%: high risk, check if investor's risk tolerance matches
- Recovery >24 months: suggests poor downside protection

---

## Fund Report Card

Write output to `data/funds/{FUND_SHORT_NAME}_report.md`:

```markdown
# {FUND NAME} — Fund Report Card
*Analysis date: {DATE} | Scheme code: {CODE} | Plan: Direct/Regular*

## ⚡ Verdict: KEEP / REVIEW / REPLACE
> [2-sentence plain-English reason]

## Returns Scorecard

| Period | Fund | Benchmark | Alpha | vs Category |
|--------|------|-----------|-------|-------------|
| 1 Year | X% | X% | +X% | [Above/Below avg] |
| 3 Year | X% | X% | +X% | [Above/Below avg] |
| 5 Year | X% | X% | +X% | [Above/Below avg] |
| SIP (3Y XIRR) | X% | — | — | — |

**Rolling return consistency (1Y periods):**
- Beat 12%: X% of all periods
- Gave negative returns: X% of all periods
- Median 1Y return: X%

## Fund Manager
Name: {MANAGER}
Tenure in this fund: {X} years
Assessment: [Consistent track record / Recent change — watch / Diluted attention]

## Portfolio Snapshot
- AUM: ₹{X} Cr
- Stocks: {N} | Top 10 concentration: {X}%
- Expense ratio: {X}% (Direct)
- Benchmark: {NAME}

**Top 5 Holdings:**
| Stock | Weight |
|-------|--------|
| {Stock} | X% |

**Sector concentration:** [Any outsized sector bets]

## Risk Profile
- Max drawdown (5Y): -{X}%
- Recovery time: {X} months
- Net alpha after TER: {+/-X}%

## Closet Indexer Check
[Pass / Flag: X% overlap with benchmark, charging X% TER for Y% net alpha]

## Recommendation
[Keep: Strong manager, consistent alpha, fair TER]
[Review: Alpha declining, manager changed, consider switching to X]
[Replace: Closet indexer / Persistent underperformance / Replace with {ALTERNATIVE}]
```

---

## Verdict criteria

**KEEP** if all of: positive 3Y alpha, manager tenure >3Y, net alpha > TER, no closet indexer flag
**REVIEW** if any of: alpha declining last 4 quarters, manager change <18 months ago, TER consuming most alpha
**REPLACE** if any of: negative 3Y alpha, closet indexer confirmed, manager gone and new manager <1Y tenure
