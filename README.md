# Quarterly Earnings & Exception-Analysis Pipeline

An automated pipeline that pulls quarterly financials for a basket of
companies and flags data-quality exceptions — missing fields, duplicate
records, statistically abnormal growth, negative equity, stale price
feeds, and EPS figures that don't reconcile against an independently
computed value.

This mirrors the "build and manage large financial data sets, perform
exception analysis, prepare quarterly earnings reports" workflow used by
buy-side financial research teams.

## What it does

1. Loads quarterly financials (revenue, net income, equity, assets,
   shares outstanding, EPS, quarter-end price) for **18 large-cap
   tickers** across **16 quarters (2022Q1–2025Q4)** into a SQLite
   warehouse.
2. Runs **6 independent exception rules** against the data.
3. Outputs a flagged-exceptions CSV, a company × exception-type heatmap,
   and per-company trend charts with flagged quarters marked.

## The 6 exception rules

| Rule | What it catches |
|---|---|
| `MISSING_FIELD` | Null in any required field (revenue, net income, equity, assets) |
| `DUPLICATE_ROW` | Exact duplicate (ticker, quarter) record |
| `YOY_GROWTH_OUTLIER` | Revenue YoY growth beyond 3 std devs of that company's *own* historical growth distribution |
| `NEGATIVE_EQUITY_OR_REVENUE` | Negative total equity or negative revenue |
| `STALE_PRICE_FEED` | Quarter-end price unchanged for 3+ consecutive quarters (broken data-feed signature) |
| `EPS_RECONCILIATION_MISMATCH` | Reported EPS doesn't match an independently computed `net_income / shares_out` within 2% tolerance |

The EPS reconciliation check is the one I'm most proud of — it's a
second, independent detection layer rather than just re-checking the
same reported numbers against each other, and it's the kind of check
most student projects skip.

### Why 3 standard deviations (not 2, or a flat %)

A flat percentage threshold penalizes naturally volatile companies and
misses anomalies in very stable ones. Using each company's *own*
historical YoY growth distribution adapts the bar to its normal
volatility. On a ~16-quarter history (≈12 usable YoY points per
company), 2 std devs starts tripping on ordinary quarterly noise
(~5% false-positive rate under a normal approximation); 3 std devs
brings that down to ~0.3% while still catching genuine anomalies. This
is a documented, defensible choice — see `exceptions.py` docstring.

## Results from this run

Out of 289 records across 18 companies, **9 exceptions** were flagged
across all 6 rule types, with **33% of companies** having at least one
flagged quarter. Full detail in `output/exceptions_flagged.csv`.

![Exception heatmap](output/exception_heatmap.png)

## Data source & reproducibility

**Tickers (fixed basket, chosen for high real-world data completeness):**
`AAPL, MSFT, GOOGL, AMZN, META, JPM, V, PG, KO, JNJ, RELIANCE.NS,
TCS.NS, HDFCBANK.NS, INFY.NS, ITC.NS, WMT, DIS, NKE`

**Period:** 2022Q1–2025Q4 (16 quarters)

**Live data:** `fetch_data_live.py` pulls this via `yfinance` — run it
locally with internet access. It writes to the exact same
`data/quarterly_financials_raw.csv` shape the rest of the pipeline
expects, so nothing else changes. Record your pull timestamp in this
README when you do (the script prints it for you).

**Sample data (used to generate the results above):**
`generate_data.py` produces a realistic synthetic dataset with the same
shape as `yfinance` output, seeded (`random_seed=42`) for
reproducibility, with 6 known issues deliberately planted so every rule
has something real to catch — documented inline in that file. This
exists because live internet access wasn't available in the environment
this was originally built in.

## Project structure

```
earnings-exception-pipeline/
├── generate_data.py        # sample data generator (documented, planted exceptions)
├── fetch_data_live.py      # swap-in: real yfinance pull
├── db.py                   # SQLite warehouse layer
├── exceptions.py           # the 6 exception rules (core logic)
├── pipeline.py             # orchestration: load -> detect -> output -> charts
├── tests/test_exceptions.py
├── memo.md                 # research memo: 3 real exceptions, explained
├── requirements.txt
├── data/                   # raw pulled data
└── output/                 # exceptions CSV, charts, SQLite db
```

## Running it

```bash
pip install -r requirements.txt --break-system-packages
python3 pipeline.py                 # runs on sample data by default
pytest tests/ -v                    # 12 unit tests, one per rule (+ edge cases)

# to use real data instead:
python3 fetch_data_live.py          # requires internet + yfinance
python3 pipeline.py                 # re-run, now reads live-pulled data
```

## What I'd do differently at scale

At 10,000 companies instead of 18, the YoY-outlier rule's per-ticker
groupby loop and the stale-price rule's per-ticker run-length scan would
both need to move from pandas `groupby` + Python loops to fully
vectorized pandas/NumPy operations — the current implementation
prioritizes readability at a scale where that trade-off is fine. The
SQLite warehouse would also need to become a proper columnar store
(e.g. Parquet + DuckDB) since single-file SQLite write contention
becomes a bottleneck past a few hundred thousand rows.

## What this project is *not*

This is a well-tested personal/academic project demonstrating exception-
detection logic — not a production-grade or enterprise data pipeline,
and it doesn't claim to prevent financial losses. Every number in this
README is checkable directly in this repo.
