---
name: quarterly-sweep
description: >
  Runs a full multi-company stock analysis sweep — fetches concalls, runs VP analysis,
  validates numbers, and outputs a ranked conviction table across your entire watchlist.
  Use when user says "run quarterly sweep", "analyze my watchlist", "quarterly results sweep",
  "update my stock tracker", "sweep all my stocks", "run analysis on all companies",
  or provides a list of symbols to analyze together. Also triggers when user asks
  "which of my stocks should I add to / trim / avoid this quarter". Reads watchlist from
  data/watchlist.csv or accepts symbols inline. Produces a ranked conviction table
  sorted by VP probability × magnitude, plus a "buy / watch / avoid" verdict per stock.
---

# Quarterly Sweep — Full Watchlist Analysis

Run the complete analysis pipeline across multiple companies in one shot and output a
ranked conviction table. This is your post-results-season command.

## When to use

- After every quarterly results season (Jan, Apr, Jul, Oct)
- When you want a ranked view across your whole watchlist
- When you want to decide where to add, trim, or exit

## Watchlist Input

**Priority order:**
1. Check if `data/watchlist.csv` exists. If yes, read symbols from the `symbol` column.
2. Check if user provided symbols inline (e.g., "sweep YATHARTH, GRSE, TATAELXSI")
3. If neither, ask: "Please share your watchlist symbols, or create data/watchlist.csv with a `symbol` column."

`data/watchlist.csv` format:
```csv
symbol,sector,entry_price,quantity
YATHARTH,Healthcare,400,100
GRSE,Defence,1200,50
TATAELXSI,Technology,6500,25
```

The `entry_price` and `quantity` columns are optional but enable portfolio-weighted scoring.

---

## Workflow

### Step 1: Load watchlist

Read `data/watchlist.csv` or parse inline symbols. Deduplicate. Print the list back to user:
"Running sweep on N companies: [SYMBOL1, SYMBOL2, ...]"

### Step 2: Per-company analysis pipeline

For EACH symbol, run these steps **sequentially within each company** (do not batch across companies — finish one before starting next, to avoid rate limit issues):

```
For each SYMBOL:
  2a. Check if concalls exist at data/companies/{SYMBOL}/concalls/
      → If not, run fetch-concalls workflow (Screener → BSE → web fallback)
      → Download latest 4 concalls
  
  2b. Run growth-trigger-analysis workflow
      → Read transcripts, build VP scorecard, extract triggers
      → Write to data/companies/{SYMBOL}/growth_trigger_analysis.md
  
  2c. Run numbers-validator workflow  
      → Fetch Screener financials
      → Validate each trigger against numbers
      → Score management credibility
      → Write to data/companies/{SYMBOL}/numbers_validation.md
  
  2d. Compute conviction score (see Step 3)
```

Print progress: "✅ SYMBOL — done (X/N)" after each company completes.

### Step 3: Compute conviction score per company

**Conviction Score (0–100):**

| Component | Weight | How to score |
|---|---|---|
| Number of validated VP triggers | 25% | ≥5 validated = 25, 3-4 = 18, 1-2 = 10, 0 = 0 |
| Management credibility score | 20% | Use score from numbers-validator directly |
| Financial trajectory | 20% | Revenue + margin both improving = 20, one improving = 12, neither = 0 |
| Promoter conviction | 15% | Buying + no pledge = 15, stable = 10, selling or pledging = 0 |
| Cycle position | 10% | Early cycle = 10, mid = 6, late = 2 |
| Kill-switch risk | 10% | No red flags = 10, 1-2 flags = 5, 3+ flags = 0 |

**Verdict:**
- 75–100: **STRONG BUY** — High VP, validated numbers, early cycle
- 55–74: **BUY / ADD** — Good story, numbers largely supportive
- 35–54: **WATCH** — Interesting thesis but unproven triggers or mixed numbers
- <35: **AVOID / TRIM** — Low conviction, red flags present

### Step 4: Build ranked conviction table

Sort all companies by Conviction Score descending. Build this output table:

```markdown
## Quarterly Sweep Results — {DATE}

| Rank | Symbol | Sector | Score | Verdict | Top VP Trigger | Key Risk | Credibility |
|------|--------|--------|-------|---------|----------------|----------|-------------|
| 1 | YATHARTH | Healthcare | 82 | STRONG BUY | Capacity ramp Q3 | Reimbursement pressure | High |
| 2 | GRSE | Defence | 71 | BUY | Order book ₹22K Cr | Execution delays | Moderate |
...
```

### Step 5: Portfolio context (if entry_price and quantity available)

If watchlist.csv has entry_price and quantity:
- Calculate current allocation weight per stock
- Flag if a STRONG BUY stock is under-allocated (<5% of portfolio)
- Flag if an AVOID stock is over-allocated (>10% of portfolio)
- Add a "Rebalance Signal" column: Add / Trim / Hold / Exit

### Step 6: Write outputs

Write sweep results to `data/sweep_{YYYY-MM}.md`:

```markdown
# Quarterly Sweep — {MONTH} {YEAR}

## Executive Summary
[3-4 sentences: What's the overall market positioning? Where is the strongest conviction concentrated? Any sector-level themes emerging?]

## Ranked Conviction Table
[Full table from Step 4]

## Rebalance Signals
[If portfolio data available: specific add/trim suggestions]

## Watch Next Quarter
[Triggers across all companies that need monitoring — what to look for in next concall]

## Companies Added to Watchlist This Sweep
[Any new high-scoring names discovered via sector research]
```

Also update `data/watchlist.csv` with a `last_score` and `last_sweep_date` column.

---

## Rate limiting

Add a 3-second pause between companies to avoid Screener rate limits:
```bash
sleep 3
```

If Screener blocks requests mid-sweep, pause for 60 seconds and resume from where you left off (track progress in `data/sweep_progress.json`).

---

## Resumable sweeps

Before starting, check if `data/sweep_progress.json` exists from a previous incomplete run:

```json
{
  "sweep_date": "2026-03",
  "total": 15,
  "completed": ["YATHARTH", "GRSE"],
  "pending": ["TATAELXSI", "..."]
}
```

If found, ask: "I found an incomplete sweep from {date}. Resume from where it left off, or start fresh?"
