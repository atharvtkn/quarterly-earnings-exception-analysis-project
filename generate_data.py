"""
generate_data.py
-----------------
Generates a REALISTIC SAMPLE quarterly-financials dataset shaped exactly like
what yfinance would return, for a fixed basket of tickers.

WHY SAMPLE DATA: this environment has no live internet access, so a real
yfinance pull can't run here. Everything downstream (SQLite schema,
exception rules, pipeline, tests) is written against this exact shape, so
swapping this file out for a real yfinance pull is a ~15-line change.
See fetch_data_live.py for that swap-in version.

We deliberately PLANT known data-quality issues into a few rows so that
when the exception rules run, we can point to specific rows and say
"yes, the pipeline correctly caught this" — this is what makes the repo
demonstrable and testable rather than just "clean data in, nothing out."

Reproducibility: fixed random seed (42), fixed ticker basket, fixed
"pull date" recorded below.
"""

import numpy as np
import pandas as pd
from datetime import datetime

RANDOM_SEED = 42
PULL_DATE = "2026-08-13"  # record the date this sample was generated

# 18 large, stable tickers (mix of US + Indian large caps) -> chosen because
# their real-world data completeness is high; this is a data-quality
# project, so we don't want flaky small-cap data undermining it.
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "JPM", "V", "PG", "KO", "JNJ",
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS",
    "WMT", "DIS", "NKE",
]

QUARTERS = pd.period_range("2022Q1", "2025Q4", freq="Q")

np.random.seed(RANDOM_SEED)


def _base_series(n, start, growth_mean=0.04, growth_std=0.06):
    """Generate a smooth-ish growing series with quarter-to-quarter noise."""
    vals = [start]
    for _ in range(n - 1):
        g = np.random.normal(growth_mean, growth_std)
        vals.append(vals[-1] * (1 + g))
    return np.array(vals)


def generate() -> pd.DataFrame:
    rows = []
    for ticker in TICKERS:
        n = len(QUARTERS)
        base_rev = np.random.uniform(2_000, 90_000)          # $mm
        base_ni_margin = np.random.uniform(0.08, 0.24)
        shares_out = np.random.uniform(500, 8_000)             # mm shares
        base_price = np.random.uniform(20, 450)

        revenue = _base_series(n, base_rev)
        net_income = revenue * (base_ni_margin + np.random.normal(0, 0.01, n))
        total_equity = _base_series(n, revenue[0] * np.random.uniform(1.5, 4), 0.03, 0.02)
        total_assets = total_equity * np.random.uniform(1.8, 3.2)
        price = _base_series(n, base_price, 0.02, 0.08)

        # reported EPS should normally == net_income / shares_out
        eps_reported = net_income / shares_out

        for i, q in enumerate(QUARTERS):
            rows.append({
                "ticker": ticker,
                "quarter": str(q),
                "revenue_mm": round(revenue[i], 2),
                "net_income_mm": round(net_income[i], 2),
                "total_equity_mm": round(total_equity[i], 2),
                "total_assets_mm": round(total_assets[i], 2),
                "shares_out_mm": round(shares_out, 2),
                "eps_reported": round(eps_reported[i], 4),
                "quarter_end_price": round(price[i], 2),
            })

    df = pd.DataFrame(rows)

    # ---- PLANT DELIBERATE EXCEPTIONS (documented here so they're auditable) ----

    # 1) Missing / null field — AAPL 2023Q3 net income goes missing
    df.loc[(df.ticker == "AAPL") & (df.quarter == "2023Q3"), "net_income_mm"] = np.nan

    # 2) Exact duplicate row — duplicate MSFT 2024Q1 row appended
    dup = df[(df.ticker == "MSFT") & (df.quarter == "2024Q1")].copy()
    df = pd.concat([df, dup], ignore_index=True)

    # 3) YoY growth outlier (>3 std devs) — INFY.NS 2024Q2 revenue spikes 5x
    #    (simulates something like an unadjusted stock-split-style data glitch)
    mask = (df.ticker == "INFY.NS") & (df.quarter == "2024Q2")
    df.loc[mask, "revenue_mm"] = df.loc[mask, "revenue_mm"] * 5.0

    # 4) Negative equity — RELIANCE.NS 2025Q1 equity goes negative
    #    (simulates a large one-off write-down/restatement)
    df.loc[(df.ticker == "RELIANCE.NS") & (df.quarter == "2025Q1"), "total_equity_mm"] = -450.0

    # 5) Stale / unchanged price series — KO price frozen for 2023Q2-2023Q4
    #    (simulates a broken data-feed signature)
    frozen_price = df.loc[(df.ticker == "KO") & (df.quarter == "2023Q2"), "quarter_end_price"].values[0]
    for q in ["2023Q2", "2023Q3", "2023Q4"]:
        df.loc[(df.ticker == "KO") & (df.quarter == q), "quarter_end_price"] = frozen_price

    # 6) EPS reconciliation mismatch — JPM 2024Q3 reported EPS doesn't match
    #    net_income / shares_out (simulates a one-off / non-recurring items
    #    adjustment that wasn't properly reflected, or a genuine data error)
    df.loc[(df.ticker == "JPM") & (df.quarter == "2024Q3"), "eps_reported"] = 12.50

    df = df.sort_values(["ticker", "quarter"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = generate()
    df.to_csv("data/quarterly_financials_raw.csv", index=False)
    print(f"Generated {len(df)} rows for {df.ticker.nunique()} tickers, "
          f"{len(QUARTERS)} quarters each (2022Q1-2025Q4).")
    print(f"Pull date recorded as: {PULL_DATE}")
    print("Planted exceptions: missing NI (AAPL), duplicate row (MSFT), "
          "revenue outlier (INFY.NS), negative equity (RELIANCE.NS), "
          "stale price (KO), EPS mismatch (JPM).")
