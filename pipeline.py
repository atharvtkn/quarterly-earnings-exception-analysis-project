"""
pipeline.py
-----------
Orchestrates the full run:
  1. Load raw quarterly financials into the SQLite warehouse
  2. Run every exception rule
  3. Write flagged exceptions to CSV
  4. Generate summary charts (per-company trend charts with exceptions
     marked, and a company x exception-type heatmap)
  5. Print a short console summary (exception count by type, % of records
     flagged)

Run with:  python3 pipeline.py
"""
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from fetch_data_live import fetch_all
from db import load_to_sqlite, read_from_sqlite
from exceptions import run_all_rules, rule_yoy_outlier


def main():
    print("=" * 60)
    print("QUARTERLY EARNINGS & EXCEPTION-ANALYSIS PIPELINE")
    print("=" * 60)

    # 1. Generate + load data
    print("\n[1/5] Generating sample quarterly financials...")
    raw = fetch_all()
    load_to_sqlite(raw)
    df = read_from_sqlite()
    print(f"      Loaded {len(df)} rows into output/warehouse.db "
          f"({df.ticker.nunique()} tickers x up to 16 quarters)")

    # 2. Run exception rules
    print("\n[2/5] Running 6 exception-detection rules...")
    flagged = run_all_rules(df)
    print(f"      {len(flagged)} exceptions flagged")

    # 3. Write CSV
    print("\n[3/5] Writing flagged exceptions to CSV...")
    flagged.to_csv(OUTPUT_DIR / "exceptions_flagged.csv", index=False)
    print("      -> output/exceptions_flagged.csv")

    # 4. Console summary stats
    print("\n[4/5] Summary:")
    by_type = flagged["exception_type"].value_counts()
    for etype, count in by_type.items():
        print(f"      {etype:<30} {count}")
    pct_flagged = 100 * flagged["ticker"].nunique() / df["ticker"].nunique()
    print(f"      {'% of companies with >=1 exception':<30} {pct_flagged:.1f}%")

    # 5. Charts
    print("\n[5/5] Generating charts...")
    _make_heatmap(flagged, df)
    _make_trend_charts(df, flagged)
    print("      -> output/exception_heatmap.png")
    print("      -> output/trend_charts/<ticker>.png")

    print("\nDone. See output/ for all artifacts.")


def _make_heatmap(flagged: pd.DataFrame, df: pd.DataFrame):
    pivot = (
        flagged.groupby(["ticker", "exception_type"])
        .size()
        .unstack(fill_value=0)
        .reindex(sorted(df["ticker"].unique()))
        .fillna(0)
    )
    plt.figure(figsize=(10, 7))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="Reds", cbar_kws={"label": "Exception count"})
    plt.title("Exception Count by Company x Type")
    plt.xlabel("Exception Type")
    plt.ylabel("Ticker")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "exception_heatmap.png", dpi=150)
    plt.close()


def _make_trend_charts(df: pd.DataFrame, flagged: pd.DataFrame):
    import os
    os.makedirs("output/trend_charts", exist_ok=True)

    # only chart companies that actually have an exception, to keep this demo-sized
    tickers_to_chart = sorted(flagged["ticker"].unique())
    yoy_df = rule_yoy_outlier(df)  # reuse to get revenue_yoy column already computed

    for ticker in tickers_to_chart:
        g = df[df.ticker == ticker].sort_values("quarter")
        exc = flagged[flagged.ticker == ticker]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(g["quarter"], g["revenue_mm"], marker="o", label="Revenue ($mm)", color="#1e4d8c")
        ax.plot(g["quarter"], g["net_income_mm"], marker="o", label="Net income ($mm)", color="#0f6b4c")
        ax.set_xticklabels(g["quarter"], rotation=45, ha="right")
        ax.set_ylim(top=ax.get_ylim()[1] * 1.22)  # headroom so annotations don't collide with title

        # annotate flagged quarters
        for _, row in exc.iterrows():
            match = g[g.quarter == row.quarter]
            if len(match):
                ax.axvline(row.quarter, color="red", alpha=0.25, linestyle="--")
                y_top = ax.get_ylim()[1] * 0.97
                ax.annotate(row.exception_type, (row.quarter, y_top),
                            fontsize=7, color="red", rotation=90, ha="center", va="top")

        ax.set_title(f"{ticker} — Revenue & Net Income (flagged quarters marked)")
        ax.legend(loc="upper left", fontsize=8)
        plt.tight_layout()
        trend_dir = OUTPUT_DIR / "trend_charts"
        trend_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(OUTPUT_DIR / "trend_charts" / f"{ticker.replace('.', '_')}.png", dpi=130)
        plt.close()


if __name__ == "__main__":
    main()
