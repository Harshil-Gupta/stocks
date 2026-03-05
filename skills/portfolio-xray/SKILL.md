---
name: portfolio-xray
description: >
  Master portfolio analyser that combines your direct Indian stocks and mutual funds into
  a single unified view — finds hidden concentration, overlap between funds and direct holdings,
  true sector exposure, and gives a complete portfolio health scorecard with rebalancing actions.
  Use when user asks "analyse my full portfolio", "what does my portfolio really look like",
  "am I over-concentrated", "portfolio review", "combine my stocks and funds analysis",
  "where am I actually exposed", or "full portfolio X-ray". This is the top-level command
  that calls Warren for stocks and mf-analyser for funds, then synthesises everything.
  Requires portfolio data as input (stocks + quantities + fund names + amounts invested).
---

# Portfolio X-Ray — Complete Portfolio Health Check

The single command that gives you the full picture: what you actually own across direct
stocks and mutual funds, where you're concentrated without knowing it, and exactly what
to do about it.

## Input Required

Warren needs your portfolio data. Accept in any of these formats:

**Format A — User pastes it inline:**
```
Direct stocks:
YATHARTH - 200 shares @ ₹420
GRSE - 50 shares @ ₹1200
HDFCBANK - 100 shares @ ₹1650

Mutual Funds:
Parag Parikh Flexi Cap - ₹2,00,000 invested
Mirae Asset Large Cap - ₹1,50,000 invested
HDFC Mid Cap Opportunities - ₹1,00,000 invested
```

**Format B — From portfolio file:**
Check `data/portfolio.csv` if it exists:
```csv
type,name,symbol_or_code,quantity_or_amount,avg_buy_price
stock,HDFC Bank,HDFCBANK,100,1650
stock,GRSE,GRSE,50,1200
fund,Parag Parikh Flexi Cap,122639,200000,
fund,Mirae Asset Large Cap,118989,150000,
```

**Format C — User uploads a screenshot or PDF of their broker/MF statement**
Extract holdings data from the document using vision/document reading.

If none of the above: ask the user to provide their holdings before proceeding.

---

## Workflow

### Phase 1: Enrich all holdings with current data (parallel)

**For each direct stock** (run in parallel):
- Get current price: WebFetch Screener or WebSearch `"{SYMBOL}" current price NSE`
- Calculate current value = quantity × current price
- Get sector from Screener

**For each mutual fund** (run in parallel):
- GET `https://api.mfapi.in/mf/search?q={FUND_NAME}` → get scheme_code
- GET `https://api.mfapi.in/mf/{scheme_code}/latest` → current NAV
- Fetch factsheet → extract top 10 holdings with weights, sector allocation, AUM
- Calculate current value = (amount_invested / purchase_NAV) × current_NAV
  - If purchase NAV not available: use invested amount as proxy and note this assumption

Report: "Portfolio loaded — {N} stocks, {M} funds. Total estimated value: ₹{X} Cr"

---

### Phase 2: Build the unified holdings map

**The core insight:** Your mutual funds own hundreds of stocks on your behalf.
A ₹2L investment in a fund that's 8% HDFC Bank means you own ₹16,000 of HDFC Bank
through that fund — on top of whatever direct HDFC Bank shares you hold.

**Aggregate stock-level exposure across everything:**

For each fund:
```
For each holding in fund's top holdings:
    Your effective exposure to that stock =
        (your fund investment ÷ fund AUM) × fund's holding in that stock × stock market cap
    
    Approximation (simpler, usually sufficient):
        Effective weight in stock = your fund value × stock's % weight in fund
```

Build a master table:

```
Stock | Direct (₹) | Via Fund A (₹) | Via Fund B (₹) | Total (₹) | % of Portfolio
HDFCBANK | 1,65,000 | 16,000 | 12,000 | 1,93,000 | 12.1%
INFY | 0 | 22,000 | 8,000 | 30,000 | 1.9%
...
```

Note: Funds only disclose top 10-15 holdings. For the remainder, map to sector level.

### Phase 3: Real sector exposure

Aggregate across everything — direct stocks + known fund holdings + fund sector allocations for unknowns:

```
Sector | Direct Stocks | Via Funds | Total | % of Portfolio
Banking & Finance | X | X | X | X%
IT | X | X | X | X%
Healthcare | X | X | X | X%
Defence | X | X | X | X%
Consumer | X | X | X | X%
...
```

### Phase 4: Fund overlap analysis

For every pair of funds in the portfolio, compute overlap:

**Overlap % = sum of min(weight_in_fund_A, weight_in_fund_B) for all common stocks**

Build an overlap matrix:

```
              Parag Parikh  Mirae Large Cap  HDFC Mid Cap
Parag Parikh      —              34%              18%
Mirae Large Cap   34%             —               22%
HDFC Mid Cap      18%            22%               —
```

**Overlap thresholds:**
- <20%: Good — funds are genuinely different
- 20–40%: Moderate — some redundancy, acceptable if both have different mandates
- >40%: High — you're paying two expense ratios for largely the same exposure
- >60%: Very high — consolidate into one fund

Also check: **Fund vs Direct Stock overlap**
If you directly own HDFCBANK and your three funds are collectively 15% HDFCBANK, you have massive concentration in one name.

### Phase 5: Concentration & risk checks

**Single stock concentration:**
Flag any stock (direct + via funds combined) that exceeds 8% of total portfolio.

**Single sector concentration:**
Flag any sector exceeding 25% of total portfolio.

**Fund count:**
- <3 funds: Possibly under-diversified
- 3-5 funds: Ideal
- >7 funds: Over-diversified, funds are probably duplicating each other, reducing to index-like returns at active fees

**Direct vs MF balance:**
Assess whether the direct equity portion is appropriate to the user's apparent sophistication
(having Warren-analyzed stocks suggests active engagement → direct equity is appropriate).

**Large cap bias check:**
Sum up exposure from large-cap index funds + large-cap direct holdings. If >70% of equity portfolio is large cap, growth potential may be limited.

**SIP vs Lumpsum:**
If user has SIP amounts, note whether SIP investments have smoothed entry costs appropriately.

### Phase 6: Performance attribution

Where possible, compute portfolio-level returns:

**Direct stocks P&L:**
- For each stock with avg_buy_price: (current_price − avg_buy_price) / avg_buy_price × 100
- Weighted average P&L across all direct holdings

**MF portfolio returns:**
- For each fund with invested amount: use NAV history to compute XIRR if dates available
- Otherwise use current value vs invested amount as rough gain%

**Overall portfolio XIRR:**
If dates are available for all investments, compute blended XIRR.

---

## Portfolio X-Ray Report

Write to `data/portfolio_xray_{YYYY-MM}.md`:

```markdown
# Portfolio X-Ray — {MONTH} {YEAR}

## Portfolio Summary
Total value: ₹{X}
Direct stocks: ₹{X} ({X}% of portfolio)
Mutual funds: ₹{X} ({X}% of portfolio)
Cash/other: ₹{X} ({X}%)

---

## 🚨 Concentration Alerts
[Each alert on its own line — these need action first]
⚠️ HDFCBANK: 14.2% of total portfolio (direct + fund exposure combined) — above 8% threshold
⚠️ Banking sector: 31% of portfolio — above 25% threshold
⚠️ Parag Parikh ↔ Mirae Large Cap: 44% overlap — consider consolidating

---

## Real Stock-Level Exposure (Top 15)

| Stock | Direct | Via Funds | Total | % Portfolio | Sector |
|-------|--------|-----------|-------|-------------|--------|
| HDFCBANK | ₹1.65L | ₹0.41L | ₹2.06L | 14.2% | Banking |
| INFY | — | ₹0.38L | ₹0.38L | 2.6% | IT |
...

*Note: Fund holdings beyond top 10 disclosed positions are mapped at sector level only.*

---

## Real Sector Exposure

| Sector | ₹ Value | % Portfolio | Assessment |
|--------|---------|-------------|------------|
| Banking & Finance | ₹X | 31% | ⚠️ Concentrated |
| IT | ₹X | 18% | ✅ Normal |
| Healthcare | ₹X | 12% | ✅ Normal |
| Defence | ₹X | 8% | ✅ Normal |
| Consumer | ₹X | 6% | ✅ Normal |

---

## Fund Overlap Matrix

| | {Fund A} | {Fund B} | {Fund C} |
|---|---|---|---|
| **{Fund A}** | — | 44% ⚠️ | 18% ✅ |
| **{Fund B}** | 44% ⚠️ | — | 22% ✅ |
| **{Fund C}** | 18% ✅ | 22% ✅ | — |

---

## Fund Verdicts

| Fund | Verdict | Reason |
|------|---------|--------|
| Parag Parikh Flexi Cap | ✅ KEEP | Consistent alpha, low overlap with others |
| Mirae Asset Large Cap | ⚠️ REVIEW | 44% overlap with PP, marginal alpha vs Nifty |
| HDFC Mid Cap Opp | ✅ KEEP | Genuine mid-cap exposure, low overlap |

*(Full fund-by-fund analysis in individual fund reports)*

---

## Direct Stock Verdicts (Warren Summary)

| Stock | Warren Score | Verdict | P&L |
|-------|-------------|---------|-----|
| YATHARTH | 82/100 | STRONG BUY | +18% |
| GRSE | 71/100 | BUY | +4% |

*(Full Warren briefs in data/companies/{SYMBOL}/warren_brief.md)*

---

## Portfolio P&L Summary

| | Invested | Current | Gain/Loss | XIRR |
|---|---|---|---|---|
| Direct stocks | ₹X | ₹X | +X% | X% |
| Mutual funds | ₹X | ₹X | +X% | X% |
| **Total** | **₹X** | **₹X** | **+X%** | **X%** |

---

## Rebalancing Actions (Priority Order)

### Immediate (do this quarter)
1. **Consolidate:** Mirae Large Cap overlaps 44% with Parag Parikh. Redeem ₹X from Mirae, add to HDFC Mid Cap or a small-cap fund for genuine diversification.
2. **Reduce HDFCBANK:** Combined exposure is 14.2%. Consider trimming direct holding by X shares to bring to <10%.

### Medium-term (next 2 quarters)  
3. **Add sector exposure:** No manufacturing/capex exposure in current portfolio. Consider adding a capital goods / infrastructure fund or direct stock.
4. **Recheck GRSE:** Warren score 71 — add if next quarter order book confirms ₹25K Cr target.

### Watch list
5. **Mirae Large Cap TER:** At 1.6% with alpha <2%, net alpha is borderline. If alpha doesn't recover in 2 quarters, replace with UTI Nifty 50 Index at 0.1% TER.

---

## What Your Portfolio Is Actually Betting On

[1-paragraph plain-English synthesis: "This portfolio is essentially a bet on India's private banking sector recovery, mid-cap capital goods growth, and one high-conviction healthcare name. You have less IT exposure than the index and almost no consumer/FMCG. The main risk is if private banks underperform — that would hit both your direct HDFC Bank holding and two of your three funds simultaneously."]
```

---

## Trigger map: what calls what

```
portfolio-xray
    │
    ├── mf-analyser          ← runs on each fund (parallel)
    │
    ├── warren               ← runs on each direct stock (parallel)
    │   ├── fetch-concalls
    │   ├── growth-trigger-analysis
    │   ├── numbers-validator
    │   └── annual-report-analyst
    │
    └── synthesise           ← portfolio-xray does this final step itself
```

**On first run:** Expect 20-40 minutes for a portfolio with 3-5 stocks and 3 funds (Warren does deep work).
**On refresh:** If Warren briefs and fund reports are <30 days old, skip re-analysis and use cached outputs. Only re-run if user says "fresh analysis" or if it's post-quarterly results.

---

## Quick mode

If user says "quick portfolio check" or "just the overview":
- Skip Warren full analysis — use last cached warren_brief.md if <60 days old
- Skip mf-analyser deep dive — use rolling returns from API only, skip factsheet fetch
- Still compute overlap matrix and concentration alerts
- Deliver the summary table in ~5 minutes instead of 30-40 minutes

Announce at start: "Running in quick mode — using cached stock analysis. Say 'full X-ray' for fresh deep dives."
