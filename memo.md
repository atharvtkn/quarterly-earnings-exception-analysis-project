# Research Memo: Notable Exceptions Found

*Pipeline run on sample data (seed=42), 18 tickers, 2022Q1–2025Q4.*

This memo walks through 3 of the 9 flagged exceptions in detail —
what was flagged, what I think caused it, and how I'd verify the true
answer in a real research setting.

---

### 1. INFY.NS, 2024Q2 — Revenue YoY growth outlier (+441.9%)

**What was flagged:** Revenue jumped from a steady growth trend to a
level 441.9% above the prior year — a >3-std-dev outlier against the
company's own 4-year growth history.

**What I think caused it:** In a real dataset, a jump this extreme and
this sudden (rather than a gradual ramp) is a classic signature of one
of: (a) an unadjusted stock split or bonus issue inflating reported
revenue-per-share-adjusted figures, (b) a reporting currency change
(e.g. a foreign subsidiary's local-currency figures accidentally left
unconverted), or (c) a genuine one-off event like a major acquisition
closing that quarter.

**How I'd verify:** Pull the company's actual quarterly filing (or
investor-relations press release) for that quarter and check the
footnotes for restatements, M&A activity, or currency-reporting changes
disclosed alongside the headline numbers. If none of those apply, I'd
next check whether the *prior-year* comparison quarter itself had an
unusually low base (which would make an otherwise normal quarter look
like a spike in YoY terms) rather than assuming the current quarter is
the anomaly.

---

### 2. JPM, 2024Q3 — EPS reconciliation mismatch (reported 12.50 vs. computed 3.49)

**What was flagged:** Reported diluted EPS of $12.50 doesn't match
`net_income / shares_out` = $3.49 — a 258% mismatch, far outside the 2%
tolerance.

**What I think caused it:** A gap this large is too big to be a rounding
or averaging-convention difference (e.g. weighted-average diluted shares
vs. period-end shares typically causes <5% gaps, not 250%+). The more
likely real-world explanation is a one-off item — a large divestiture
gain, tax benefit, or discontinued-operations adjustment — being
included in reported EPS but not reflected in the net income and shares
figures I pulled, or a units/scaling error somewhere in the data source
(e.g. EPS reported in cents vs. dollars).

**How I'd verify:** Check whether the company reported both a "GAAP EPS"
and an "adjusted/non-GAAP EPS" that quarter — if the two differ by
roughly this ratio, that's almost certainly the answer, and the fix is
pulling both explicitly rather than a single ambiguous EPS field.

---

### 3. KO, 2023Q2–2023Q4 — Stale price feed (3 consecutive quarters)

**What was flagged:** Quarter-end price identical across three
consecutive quarters — a pattern that's essentially impossible for an
actively traded large-cap stock and points to a broken or stale data
feed rather than genuine price stability.

**What I think caused it:** Most likely a data-pull failure where the
fetch silently fell back to a cached/last-known value instead of
erroring, rather than any real market behavior.

**How I'd verify:** Cross-check the flagged dates against a second
independent price source (e.g. a different data vendor or the
exchange's own closing-price archive). If the second source shows the
price actually moved, that confirms the first feed was stale and the
fix is adding a "last-updated" freshness check upstream of ingestion,
not a downstream statistical rule.

---

## General takeaway

All three cases above illustrate the same core distinction that matters
for this kind of work: a flagged exception is a *hypothesis*, not a
verdict. The pipeline's job is to surface the anomaly and a plausible
first explanation cheaply and consistently; a human still has to decide
whether it's a data-quality problem (fix the pipeline) or a genuine
business event (write it up as a finding).
