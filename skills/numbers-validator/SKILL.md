---
name: numbers-validator
description: >
  Cross-checks what management claims in concall transcripts against actual financial numbers
  from Screener.in — catches overpromising, validates VP triggers, and surfaces red flags.
  Use when user asks to "validate numbers for [SYMBOL]", "fact-check management claims for [SYMBOL]",
  "cross-check concall vs financials", "numbers check on [SYMBOL]", or after running
  growth-trigger-analysis and wanting to verify if the triggers are backed by real financial
  evidence. Also auto-invoked as Step 5 in full VP analysis. Outputs a Numbers Validation
  Report with a management credibility score and a clean/red-flag verdict per VP trigger.
---

# Numbers Validator — Management Claims vs Financial Reality

Cross-check what management says on concalls against what Screener.in financials actually show.
Produces a credibility assessment and per-trigger validation that feeds back into your VP scorecard.

## When to use

- After `growth-trigger-analysis` produces a VP scorecard, run this to validate each trigger
- Standalone: "fact-check TATAELXSI management claims"
- Automatically: any full-stock analysis workflow should run this before conviction rating

## Data Sources

Primary: `https://www.screener.in/company/{SYMBOL}/consolidated/`
Fallback: `https://www.screener.in/company/{SYMBOL}/`

Extract from Screener:
- Revenue (quarterly + annual, last 8 quarters)
- EBITDA / Operating profit margins (last 8 quarters)
- PAT and PAT margins
- Cash from operations (last 3 years)
- Debt / Net debt trajectory
- Promoter holding % (last 4 quarters)
- Return on equity / Return on capital employed (last 3 years)
- Order book or backlog (if shown)
- Inventory days, debtor days (working capital health)

If Screener is insufficient for sector-specific metrics (e.g., AUM for financials, occupancy for hospitals), WebSearch `"{COMPANY_NAME}" investor presentation {CURRENT_YEAR}` to supplement.

---

## Workflow

### Step 1: Load VP triggers

Check if `data/companies/{SYMBOL}/growth_trigger_analysis.md` exists.
- If yes: read it and extract the "Growth Triggers" list and VP Scorecard
- If no: ask user to run growth-trigger-analysis first, OR proceed with raw concall claims extracted from `data/companies/{SYMBOL}/concalls/` if those exist

### Step 2: Fetch financial data from Screener

WebFetch the Screener page. Extract a structured data table with the metrics listed above. Pay special attention to:

**Trajectory, not snapshot.** A single year means nothing. You want direction:
- Is revenue growth accelerating or decelerating over 8 quarters?
- Are margins expanding QoQ or compressing despite volume growth claims?
- Is cash flow from operations tracking PAT, or is there a growing divergence (working capital trap)?
- Is debt going up while management says they're "asset-light" or "debt-free"?

### Step 3: Match management claims to numbers

For each VP trigger / management claim, create a validation entry:

**Validation logic:**

| Claim Type | What to check |
|---|---|
| "Revenue to double in X years" | Current CAGR trajectory — is it on track? |
| "Margin expansion from operating leverage" | Are margins actually expanding as revenue grows? |
| "Debt-free / deleveraging" | Is net debt declining in absolute terms? |
| "Order book provides visibility" | Has revenue execution matched past order book claims? |
| "Capacity addition will drive growth" | Is capex actually showing up in fixed assets? |
| "Market share gains" | Is revenue growing faster than sector peers? |
| "Working capital improvement" | Are debtor days / inventory days actually shrinking? |
| "Asset-light model" | Is CFO/PAT ratio > 0.8 sustainably? |
| "Premiumisation" | Are realisations per unit rising? |

### Step 4: Promoter conviction check

- Promoter holding trend: increasing = positive signal, decreasing = red flag
- Pledged % of promoter holding: >20% is a structural risk, >40% is a kill-switch
- Any bulk deal activity in last 2 quarters (institutional accumulation or exit)

### Step 5: Management credibility score

Look back at the last 4 quarters. For each quarter where management gave specific guidance (numbers, timelines):
- Did they meet it? (+1)
- Did they miss by <10%? (0)
- Did they miss by >10% or walk it back? (-1)

**Credibility Score = (hits - misses) / total guided items × 100**

Classify:
- 80–100: High credibility — take guidance at face value
- 50–79: Moderate — apply 20% haircut to forward projections
- <50: Low credibility — treat all guidance as aspirational, demand evidence

### Step 6: Red flags checklist

Flag if ANY of these are true:
- [ ] Revenue growth claim not supported by last 4Q trajectory
- [ ] PAT growing but CFO flat or declining (accrual manipulation risk)
- [ ] Debt rising while claiming "asset-light" or "deleveraging"
- [ ] Promoter pledging >20%
- [ ] Margins compressed for 3+ quarters despite volume growth claims
- [ ] Inventory days or debtor days rising >15% YoY
- [ ] Capex guidance not showing up in balance sheet
- [ ] Management missed own guidance >2 times in last 4 quarters

### Step 7: Write output

Write to `data/companies/{SYMBOL}/numbers_validation.md`:

```markdown
# {SYMBOL} — Numbers Validation Report

## Financial Snapshot (last 8 quarters)
[compact table: Revenue, EBITDA%, PAT, CFO, Net Debt, Promoter%]

## Management Credibility Score
Score: XX/100 — [High / Moderate / Low]
Evidence: [3-4 bullet summary of guidance hits and misses]

## Trigger Validation

### ✅ VALIDATED triggers (numbers support the claim)
- [Trigger]: [Evidence from financials]

### ⚠️ UNPROVEN triggers (claim made, no financial evidence yet)
- [Trigger]: [What would need to show up to validate]

### ❌ CONTRADICTED triggers (numbers contradict the claim)
- [Trigger]: [What the numbers actually show]

## Red Flags
[List any red flags found, or "None identified"]

## Promoter Conviction
[Holding trend + pledging status]

## Verdict
[1-paragraph synthesis: Is the VP story supported by the numbers?
What is the single biggest risk to the thesis?]
```

## Integration with growth-trigger-analysis

After this skill runs, the VP scorecard should be updated mentally:
- Validated triggers → increase Probability score
- Contradicted triggers → move to Kill-Switch column
- Low credibility score → apply uniform 20-30% discount to all timing estimates

The combination of qualitative VP (from concalls) + quantitative validation (from this skill) gives you a complete buy-side picture.
