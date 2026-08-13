"""
fetch_data_live.py
-------------------
LIVE version of generate_data.py, for running on your own machine with
internet access. Swaps the synthetic generator for real yfinance pulls.

Usage:
    pip install yfinance --break-system-packages   # or in a venv
    python3 fetch_data_live.py

This writes data/quarterly_financials_raw.csv in the EXACT same shape
generate_data.py produces, so pipeline.py, exceptions.py, and the tests
all work unchanged -- just point pipeline.py at this file instead (see
the one-line note at the bottom of pipeline.py's imports).

IMPORTANT: record the exact pull date/time below for reproducibility --
the README's "Data source" section should match what you record here.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

from generate_data import TICKERS  # reuse the same fixed basket

PULL_TIMESTAMP = datetime.now().isoformat()


def fetch_ticker(ticker: str) -> pd.DataFrame:
    """Pull quarterly financials + price for one ticker via yfinance."""
    t = yf.Ticker(ticker)

    q_financials = t.quarterly_financials.T      # revenue, net income, etc.
    q_balance = t.quarterly_balance_sheet.T       # equity, assets
    q_price_hist = t.history(period="4y", interval="3mo")

    if q_price_hist.index.tz is not None:
        q_price_hist.index = q_price_hist.index.tz_localize(None)

    rows = []
    for period_end, fin_row in q_financials.iterrows():
        quarter = pd.Period(period_end, freq="Q")
        bal_row = q_balance.loc[period_end] if period_end in q_balance.index else None

        revenue = fin_row.get("Total Revenue")
        net_income = fin_row.get("Net Income")
        total_equity = bal_row.get("Stockholders Equity") if bal_row is not None else None
        total_assets = bal_row.get("Total Assets") if bal_row is not None else None
        shares_out = t.info.get("sharesOutstanding", None)
        eps_reported = fin_row.get("Diluted EPS") or fin_row.get("Basic EPS")

        # nearest price to period_end as a simple quarter-end proxy
        price_row = q_price_hist.asof(period_end) if len(q_price_hist) else None
        price = price_row["Close"] if price_row is not None else None

        rows.append({
            "ticker": ticker,
            "quarter": str(quarter),
            "revenue_mm": (revenue / 1e6) if revenue is not None else None,
            "net_income_mm": (net_income / 1e6) if net_income is not None else None,
            "total_equity_mm": (total_equity / 1e6) if total_equity is not None else None,
            "total_assets_mm": (total_assets / 1e6) if total_assets is not None else None,
            "shares_out_mm": (shares_out / 1e6) if shares_out else None,
            "eps_reported": eps_reported,
            "quarter_end_price": price,
        })
    return pd.DataFrame(rows)


def fetch_all() -> pd.DataFrame:
    frames = []
    for ticker in TICKERS:
        try:
            df = fetch_ticker(ticker)
            frames.append(df)
            print(f"  fetched {ticker}: {len(df)} quarters")
        except Exception as e:
            print(f"  WARNING: failed to fetch {ticker}: {e}")
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    print(f"Pulling live data at {PULL_TIMESTAMP} for {len(TICKERS)} tickers...")
    df = fetch_all()
    df.to_csv("data/quarterly_financials_raw.csv", index=False)
    print(f"\nSaved {len(df)} rows to data/quarterly_financials_raw.csv")
    print(f"RECORD THIS PULL DATE IN YOUR README: {PULL_TIMESTAMP}")