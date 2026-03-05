---
name: idea-generator
description: >
  Generates new investment ideas — stocks AND/OR mutual funds — contextually aware of what
  the user already owns. Fills gaps in the existing portfolio, avoids duplication, matches
  the user's demonstrated investment style, and always gives a specific stocks-vs-MF
  deployment recommendation for fresh capital. Triggers when user says "suggest new stocks",
  "what else should I buy", "where should I put this money", "find me new ideas",
  "I have X rupees to invest", "what funds should I add", "give me multibagger ideas",
  "I sold X and have cash to deploy", "suggest alternatives to [stock]", or any request
  for new investment ideas beyond current holdings. Always reads existing portfolio first
  before suggesting anything. Pairs with Warren for deep-dive validation of top picks.
---

# Idea Generator — New Stock & MF Ideas, Contextually Aware

Generate high-quality new investment ideas that complement what the user already owns —
no duplicates, no filling gaps they don't need, and always a clear stocks-vs-MF recommendation
for the capital in question.

## Core Philosophy

**Bad idea generators dump a list of screener results.**
**Good idea generators ask: given what you already own, what are you missing?**

Every idea here must pass three filters before surfacing to the user:
1. **Non-overlapping** — not already in portfolio, not duplicating a sector/theme already well-represented
2. **Contextually additive** — fills a real gap (sector, market cap, geography) in the existing portfolio
3. **Has a thesis** — a specific reason why this specific stock/fund, why now, with a falsifier

---

## Step 1: Load and understand the existing portfolio

Before generating a single idea, read the portfolio. Priority order:
1. Check `data/portfolio_xray_{latest}.md` — if portfolio X-ray was run recently, use its sector map
2. Check `data/portfolio.csv` or `data/watchlist.csv`
3. If user pasted holdings inline, parse them
4. If nothing available, ask: "Can you share your current holdings? Even a rough list helps me avoid suggesting what you already own."

From the portfolio, extract:
- **Sectors already owned** and their weights
- **Market cap mix** (large/mid/small cap split, approximate)
- **MF categories already held** (large cap, small cap, mid cap, flexi cap, sectoral, etc.)
- **Investment style signals** — does the user own quality compounders (HDFC Bank, Asian Paints), growth plays (Persistent, CDSL), or deep cyclicals (chemicals, defence)? All three = balanced style.
- **Geographic exposure** — any international funds/ETFs?
- **Gaps** — what sectors/themes are absent that could add genuine diversification?

Announce what you found: *"I can see your portfolio is heavy on IT (21%) and Specialty Chemicals (10%), with good exposure to pharma and banking. Here's what you're missing and what I'd suggest..."*

---

## Step 2: Identify portfolio gaps

Map the user's current sector exposure against a well-diversified Indian equity portfolio. Flag genuine gaps:

**Common gaps to check for:**
- **Consumer Discretionary / Retail** (not just FMCG) — rising aspirational India
- **Healthcare services** (hospitals, diagnostics) vs just pharma manufacturers
- **Capital goods / Infrastructure** — India's capex cycle
- **Real estate / REITs** — if no real estate exposure at all
- **Renewable energy / Clean tech** — structural 10-year theme
- **Global / International** — rupee depreciation hedge
- **Fintech / New-age platforms** — if portfolio is only traditional finance
- **Agri / Food processing** — often completely absent in urban portfolios
- **Defence & Aerospace** — multi-year government capex
- **Specialty Retail** (organized retail chains) — unorganised → organised shift

Also check market cap gaps:
- If portfolio is 80%+ large cap → suggest quality mid/small cap ideas
- If portfolio is 80%+ small/mid → suggest anchoring with some large cap quality
- If no international exposure → suggest 3–5% international ETF allocation

---

## Step 3: Generate stock ideas

For each gap identified, generate 2–3 stock candidates. Then **rank and keep only the best 1–2 per gap** — do not dump 30 names on the user.

### How to source ideas (in order of priority)

**Source A — Sector leaders with VP potential:**
WebSearch `"best [sector] stocks India 2025 2026 analyst picks"` + WebFetch Screener screens.
Focus on: market leaders with expanding TAM, or #2 players taking market share from leaders.

**Source B — Screener-based screening:**
WebFetch `https://www.screener.in/explore/` to find companies with:
- Revenue CAGR >15% last 3 years
- ROCE >15%
- Debt/Equity <0.5
- Promoter holding >50%
- Market cap ₹500Cr to ₹20,000Cr (sweet spot for multibagger potential)

**Source C — Thematic/structural searches:**
WebSearch for: India government capex beneficiaries, PLI scheme winners, China+1 beneficiaries, domestic consumption plays, import substitution stories.

**Source D — Analyst and fund manager high-conviction picks:**
WebSearch `"top stock picks [sector] India [current year] fund manager"` — look for names that appear across multiple analyst reports (consensus among smart money = higher signal).

### For each candidate stock, validate quickly:

Before recommending, do a 10-minute sanity check:
1. WebFetch Screener page — check if revenue and PAT are both growing last 4 quarters
2. Check promoter holding >50% and not declining
3. Check debt — prefer net cash or low debt/equity
4. Check current valuation vs 3-year average PE — is it at a reasonable entry point?
5. Quick news check — any recent negative events (SEBI action, fraud allegations, management exit)?

If a stock fails any of these, replace it with the next candidate. **Do not recommend a stock you haven't sanity-checked.**

### Stock idea output format

For each recommended stock:

```
## [COMPANY NAME] (SYMBOL) — [Sector]
Current price: ₹XXX | Market cap: ₹X,XXX Cr | Category: Large/Mid/Small cap

**Why this, why now:**
[2–3 sentences: specific structural thesis, not generic. What is the variant perception?
What does the market underestimate about this company right now?]

**What makes it a fit for your portfolio:**
[1 sentence: what gap does this fill that your current holdings don't cover?]

**Key numbers (from Screener):**
- Revenue growth (3Y CAGR): X%
- ROCE: X% | Debt/Equity: X
- Promoter holding: X% ([increasing/stable/declining])
- PE vs 3Y avg: trading at [premium/discount] to historical average

**What to watch (the falsifier):**
[1 specific thing that, if it happens, means the thesis is broken and you should exit]

**Suggested allocation:** X% of fresh capital (₹X,XXX if investing ₹X total)

**Warren deep-dive:** Say "Warren analyze [SYMBOL]" for complete concall + governance analysis
```

---

## Step 4: Generate MF ideas (always alongside stocks)

**The stocks-vs-MF decision framework:**

Present this to the user upfront, then make a recommendation:

| Situation | Lean toward MFs | Lean toward Direct Stocks |
|-----------|----------------|--------------------------|
| Amount available | <₹50,000 | >₹1,00,000 |
| Time to monitor | Low (<1hr/month) | High (willing to track quarterly) |
| Sector expertise | Unfamiliar with the sector | Deep understanding |
| Market cap | Small/micro cap | Large/mid cap |
| Portfolio already | Too many direct stocks (>25) | Too few direct stocks (<10) |
| Conviction level | "Interesting sector, unsure which stock" | "I know exactly which company" |

**Recommendation logic:**
- If user is deploying <₹50,000: **strongly recommend MF route** — transaction costs + tracking effort for a small direct stock position don't justify it
- If sector is unfamiliar (e.g., chemicals, defence for a generalist investor): **recommend a sector ETF or thematic fund** over stock-picking
- If user already has >20 direct stocks: **recommend adding via MF** to reduce portfolio complexity
- If user wants international exposure: **must go MF/ETF route** (LRS limits aside)

### MF idea sourcing

For each category gap:

**Step 4a — Category check:**
What MF categories does the user already hold? Map against:
- Large cap fund / Nifty 50 index
- Flexi cap / Multi cap
- Mid cap fund
- Small cap fund
- Sector / Thematic fund
- International fund
- Hybrid / Balanced advantage

**Step 4b — Find top performers in missing categories:**
WebFetch `https://api.mfapi.in/mf/search?q={CATEGORY}` to get scheme codes.
WebSearch `"best [category] mutual fund India direct plan 2025 2026"` — look for consistent names across Value Research, Morningstar, and Moneycontrol.

**Step 4c — Validate with rolling returns:**
For each candidate fund, GET `https://api.mfapi.in/mf/{SCHEME_CODE}` and compute:
- 3Y rolling return median
- % of 3Y periods that beat benchmark
- Max drawdown last 3 years

Keep only funds where 3Y rolling return median >benchmark median AND manager tenure >2 years.

### MF idea output format

```
## [FUND NAME] — [Category]
AMC: [AMC name] | Plan: Direct | Scheme code: XXXXX

**Why this fund:**
[2–3 sentences: what gap it fills, why this specific fund over alternatives in the same category]

**Performance:**
- 3Y CAGR: X% vs benchmark X%
- Rolling return consistency: beats benchmark in X% of 3Y periods
- Max drawdown (3Y): -X%
- Fund manager: [Name], [X] years in this fund

**Suggested deployment:**
- Lumpsum: ₹X,XXX (if market is at or below 52-week average PE)
- SIP: ₹X,XXX/month for [X] months
- Or: ₹X,XXX lumpsum + ₹X,XXX/month SIP going forward

**Overlap with existing holdings:**
[Does this fund overlap significantly with Axis Small Cap / Nippon / PGIM already held?
Quantify if possible.]
```

---

## Step 5: Deployment plan for specific capital amounts

When the user has a specific amount to invest (e.g., "I got ₹1.27L from exits, where do I put it?"):

Structure the recommendation as a **specific allocation table**:

```
## Deployment Plan for ₹{AMOUNT}

### Recommended split: X% stocks / Y% MF / Z% hold

| Destination | Type | Amount | Rationale |
|-------------|------|--------|-----------|
| [STOCK/FUND 1] | Direct stock / MF | ₹XX,XXX | [1-line reason] |
| [STOCK/FUND 2] | Direct stock / MF | ₹XX,XXX | [1-line reason] |
| [STOCK/FUND 3] | Direct stock / MF | ₹XX,XXX | [1-line reason] |
| Hold as cash buffer | — | ₹XX,XXX | [if market seems extended] |

### Deployment timing
[Lumpsum vs SIP guidance based on current market conditions]
- If Nifty PE < 20: Deploy 100% lumpsum
- If Nifty PE 20–24: Deploy 50% now, 50% over 3 months via SIP
- If Nifty PE > 24: Deploy 30% now, rest via monthly SIP over 6 months

### What NOT to do with this money
[Specific names/categories to avoid — e.g., "don't add to IT sector, you're already at 21%",
"avoid small-cap lumpsum in current market conditions"]
```

---

## Step 6: Output and integration

Write idea output to `data/new_ideas_{YYYY-MM}.md`.

Always end with:

```
## Next steps
- For any stock above, say "Warren analyze [SYMBOL]" to get full concall + governance diligence
- For any MF above, say "analyse [fund name]" to get rolling return + manager deep-dive
- To see how these fit into your full portfolio, say "run portfolio X-ray" after adding them
```

---

## What this skill does NOT do

- Does not recommend penny stocks or stocks below ₹500Cr market cap without explicit user request
- Does not suggest more than 5–6 new names at once — better to go deep on 5 than shallow on 20
- Does not recommend any stock without at least a Screener sanity check first
- Does not recommend Regular plan MFs — always Direct
- Does not suggest sector funds as core portfolio holdings — only as tactical/satellite positions
- Does not recommend adding to sectors already >15% of portfolio unless there is a very specific variant perception reason
- Never says "this is not financial advice" as a disclaimer — the user knows this is AI-generated research, not SEBI-registered advice. Just be honest about uncertainty instead.

---

## Handling the stocks-vs-MF question directly

If the user asks "should I put this in stocks or a mutual fund?", answer it directly using this logic:

**Recommend stocks if:**
- Amount > ₹1L AND user has shown they track quarterly results
- There is a specific high-conviction idea with a clear VP thesis
- The sector is one the user already understands (evidenced by their existing holdings)
- Portfolio has <20 direct stock positions (room for more without losing focus)

**Recommend MF if:**
- Amount < ₹50K (transaction costs and tracking overhead don't justify direct stocks)
- The gap is in a sector the user has zero existing exposure to (learning curve risk)
- User already has >25 direct stocks (adding more worsens the concentration-by-dilution problem)
- The idea is thematic/macro ("I want to bet on India's infra boom") rather than company-specific
- Market cap target is small/micro cap (fund manager's research advantage > individual investor's)

**Recommend split (50% stocks / 50% MF) if:**
- Amount is ₹50K–₹1L
- User has moderate portfolio complexity already
- The sector has 1–2 clear stock leaders but also benefits from broader fund exposure
