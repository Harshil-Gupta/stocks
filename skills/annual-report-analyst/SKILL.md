---
name: annual-report-analyst
description: >
  Deep-reads company annual reports to extract what management does NOT say on concalls —
  related-party transactions, auditor qualifications, contingent liabilities, director changes,
  remuneration vs performance, and capital allocation quality. Use when user asks to
  "analyze annual report for [SYMBOL]", "read AR for [SYMBOL]", "check annual report red flags",
  "audit the annual report", "what's hidden in the AR", or "governance check on [SYMBOL]".
  Also triggers when growth-trigger-analysis shows Low management credibility and deeper
  governance diligence is needed. Produces a Governance & Capital Allocation scorecard
  that is the single best kill-switch filter before buying a stock.
---

# Annual Report Analyst — Governance, Red Flags & Capital Allocation

Read the annual report the way an activist short-seller would — looking for what management
conceals, understates, or buries in footnotes. Then score governance quality.

## When to use

- Before initiating a new position (especially mid/small cap)
- When management credibility score from numbers-validator is <60
- When promoter pledging is >15% or promoter holding is declining
- When CFO/PAT ratio is persistently <0.7 (possible accrual issues)
- Any time you want the deepest kill-switch filter on a stock

## Finding the Annual Report

### Step 1: Locate the latest AR

Try in order:
1. Check `data/companies/{SYMBOL}/annual_reports/` for existing AR PDFs
2. WebFetch `https://www.screener.in/company/{SYMBOL}/consolidated/` — look for "Annual Report" links
3. WebSearch `"{COMPANY_NAME}" annual report {CURRENT_YEAR} site:bseindia.com`
4. WebSearch `"{COMPANY_NAME}" annual report {CURRENT_YEAR} filetype:pdf`

Download to `data/companies/{SYMBOL}/annual_reports/{SYMBOL}_AR_{YEAR}.pdf`

Focus on the **most recent AR**. If it's more than 14 months old, flag this — a delayed AR is itself a red flag.

---

## What to read (and in what order)

Annual reports are long. Read these sections in priority order, not cover-to-cover:

### Priority 1: Auditor's Report (pages vary, search for "Independent Auditor")

This is the single most important section. Look for:

**Audit opinion type:**
- Unqualified (clean) = baseline expectation, not a positive signal
- Qualified = serious red flag, understand the qualification precisely
- Emphasis of Matter = yellow flag, read the paragraph carefully
- Adverse opinion = exit signal

**Key Audit Matters (KAM):** These are areas the auditor found complex or risky. Extract each KAM and the auditor's conclusion. A KAM on revenue recognition or related-party transactions deserves special attention.

**CARO (Companies Auditor's Report Order) observations:** Look for adverse remarks on:
- Loans to related parties
- Utilization of funds raised (IPO/QIP proceeds actually deployed as stated?)
- Default on loans / dues
- Fraud reported during the year

### Priority 2: Related Party Transactions (RPT) Note

Find the RPT disclosure (usually in Notes to Accounts). Extract:
- All entities where promoter/directors have an interest
- Volume of transactions: sales to, purchases from, loans given to/received from related parties
- Whether RPT terms are "at arm's length" (management always claims this — verify by comparing rates)

**Red flags in RPTs:**
- Loans given TO related parties (cash leaving the listed company)
- Purchases FROM promoter-owned entities at above-market prices
- Sales TO promoter entities at below-market prices
- RPT volume growing faster than core revenue
- Any RPT not approved by the Audit Committee

### Priority 3: Contingent Liabilities

Find the "Contingent Liabilities" note. These are off-balance-sheet risks:
- Tax demands under dispute: is the total material vs. net worth?
- Legal cases: any large pending litigation that could impair the business?
- Guarantees given on behalf of subsidiaries or related parties
- Export/import obligation defaults

Flag if total contingent liabilities > 20% of net worth.

### Priority 4: Management Discussion & Analysis (MD&A)

Read for:
- Specific guidance with numbers (these become falsifiable claims for next year)
- Capital allocation plan: where is the cash going?
- Risk factors section: what does management itself admit as risks? (Boilerplate vs genuine)
- Segment performance: is the "growth segment" actually growing?

### Priority 5: Director Remuneration vs Performance

Extract from the Corporate Governance section:
- CEO/MD remuneration (total, including ESOPs)
- Company's PAT and revenue growth in the same year
- Remuneration as % of PAT
- Whether remuneration grew faster than PAT (misaligned incentives flag)

**Red flags:**
- Remuneration up YoY while PAT declined
- Commission to promoter-directors >5% of PAT
- Large ESOPs granted at deep discounts during a down year

### Priority 6: Capital Allocation Quality

From Cash Flow Statement + Balance Sheet:
- CFO / PAT ratio over 3 years (should be >0.8 consistently)
- Capex intensity: is it building capacity or just maintenance?
- Dividend payout ratio: growing, stable, or cut when they needed to?
- Acquisitions: did they overpay? Any goodwill impairment?
- Cash and equivalents vs debt: net cash or net debt?

### Priority 7: Director & KMP Changes

From Corporate Governance / Notices:
- Any independent director resignations in the year?
- CFO or Company Secretary change? (High turnover at CFO level = serious red flag)
- New directors: any red flags on their other directorships?

---

## Governance Scorecard

Score each dimension 0–10:

| Dimension | Score | Notes |
|---|---|---|
| Auditor opinion quality | /10 | Clean=8-10, KAMs but clean=6-7, Qualified=0-3 |
| RPT cleanliness | /10 | No RPTs=10, Small arm's-length=7, Loans to RPT=0-3 |
| Contingent liability risk | /10 | <5% net worth=10, 5-20%=6, >20%=2 |
| Promoter remuneration alignment | /10 | Proportional to performance=8-10, Misaligned=0-4 |
| Capital allocation quality | /10 | High CFO/PAT + sensible capex=8-10 |
| KMP stability | /10 | No changes=10, CFO/CS change=4 |
| **Total Governance Score** | **/60** | |

**Verdict:**
- 48–60: Strong governance — proceed with VP analysis with confidence
- 36–47: Adequate — monitor RPTs and remuneration annually
- 24–35: Weak governance — apply significant valuation discount, position size down
- <24: Governance risk — avoid regardless of VP story

---

## Output

Write to `data/companies/{SYMBOL}/ar_analysis.md`:

```markdown
# {SYMBOL} — Annual Report Analysis ({YEAR})

## Auditor Opinion
Type: [Unqualified / Qualified / Adverse]
Key Audit Matters: [list with auditor conclusions]
CARO observations: [list or "None adverse"]

## Related Party Transactions
[Table of material RPTs with amounts and red flag assessment]

## Contingent Liabilities
Total: ₹XX Cr vs Net Worth ₹XX Cr ([X]% of net worth)
[List material items]

## MD&A — Specific Guidance Extracted
[Falsifiable forward claims with numbers and timelines]

## Remuneration vs Performance
CEO/MD total remuneration: ₹XX Cr
PAT growth YoY: [+/-X%]
Remuneration as % of PAT: X%
Assessment: [Aligned / Misaligned]

## Capital Allocation Quality
3-year CFO/PAT ratio: [X.X]
Key capex: [what it's building]
Dividend policy: [growing/stable/cut]

## Director/KMP Changes
[Any changes flagged, or "No material changes"]

## Governance Scorecard
[Table with scores]
Total: XX/60 — [Strong / Adequate / Weak / Avoid]

## Kill-Switch Findings
[Anything that should stop you from investing, regardless of VP story]

## Green Flags
[Any unusually positive governance signals]
```

---

## Integration with other skills

- Run this BEFORE initiating a position when numbers-validator flags credibility <60
- Any "Qualified" auditor opinion or RPT loan to related party = automatic kill-switch in VP scorecard
- Governance Score feeds into the quarterly-sweep conviction score as a modifier:
  - Score 48–60: no adjustment
  - Score 36–47: subtract 5 from conviction score
  - Score <36: subtract 15 from conviction score
