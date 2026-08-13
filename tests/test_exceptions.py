"""
tests/test_exceptions.py
-------------------------
Unit tests for exceptions.py. Each test builds a tiny, hand-crafted
DataFrame with ONE known issue and asserts the corresponding rule catches
it -- and, just as importantly, that clean rows are NOT flagged (no false
positives). Run with:  pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from exceptions import (
    rule_missing_field,
    rule_duplicate_row,
    rule_yoy_outlier,
    rule_negative_equity_or_revenue,
    rule_stale_price,
    rule_eps_reconciliation,
    run_all_rules,
)


def _clean_row(ticker="TEST", quarter="2024Q1", **overrides):
    row = {
        "ticker": ticker,
        "quarter": quarter,
        "revenue_mm": 1000.0,
        "net_income_mm": 150.0,
        "total_equity_mm": 2000.0,
        "total_assets_mm": 4000.0,
        "shares_out_mm": 100.0,
        "eps_reported": 1.50,       # == 150 / 100, reconciles exactly
        "quarter_end_price": 50.0,
    }
    row.update(overrides)
    return row


def test_missing_field_catches_null():
    df = pd.DataFrame([_clean_row(net_income_mm=np.nan)])
    flagged = rule_missing_field(df)
    assert len(flagged) == 1
    assert flagged.iloc[0]["exception_type"] == "MISSING_FIELD"


def test_missing_field_no_false_positive_on_clean_row():
    df = pd.DataFrame([_clean_row()])
    assert len(rule_missing_field(df)) == 0


def test_duplicate_row_catches_exact_duplicate():
    df = pd.DataFrame([_clean_row(), _clean_row()])
    flagged = rule_duplicate_row(df)
    assert len(flagged) == 2  # both copies flagged


def test_duplicate_row_no_false_positive_on_different_quarters():
    df = pd.DataFrame([_clean_row(quarter="2024Q1"), _clean_row(quarter="2024Q2")])
    assert len(rule_duplicate_row(df)) == 0


def test_yoy_outlier_catches_extreme_spike():
    rows = []
    # 15 quarters of steady ~5% growth (stable baseline, like a real
    # company's history), then a final quarter spikes 10x -- mirrors how
    # the rule is actually used: judged against that company's own
    # established normal range, not a handful of noisy points.
    rev = 1000.0
    years = [2021, 2022, 2023, 2024]
    quarters = [f"{y}Q{q}" for y in years for q in range(1, 5)][:15]
    for q in quarters:
        rows.append(_clean_row(quarter=q, revenue_mm=rev))
        rev *= 1.05
    rows.append(_clean_row(quarter="2025Q1", revenue_mm=rev * 10))
    df = pd.DataFrame(rows)
    flagged = rule_yoy_outlier(df)
    assert len(flagged) >= 1
    assert "YOY_GROWTH_OUTLIER" in flagged["exception_type"].values


def test_negative_equity_catches_negative_value():
    df = pd.DataFrame([_clean_row(total_equity_mm=-100.0)])
    flagged = rule_negative_equity_or_revenue(df)
    assert len(flagged) == 1


def test_negative_equity_no_false_positive_on_positive_value():
    df = pd.DataFrame([_clean_row()])
    assert len(rule_negative_equity_or_revenue(df)) == 0


def test_stale_price_catches_frozen_feed():
    rows = [
        _clean_row(quarter="2023Q1", quarter_end_price=50.0),
        _clean_row(quarter="2023Q2", quarter_end_price=50.0),
        _clean_row(quarter="2023Q3", quarter_end_price=50.0),
    ]
    df = pd.DataFrame(rows)
    flagged = rule_stale_price(df, min_consecutive=3)
    assert len(flagged) >= 1


def test_stale_price_no_false_positive_on_moving_price():
    rows = [
        _clean_row(quarter="2023Q1", quarter_end_price=50.0),
        _clean_row(quarter="2023Q2", quarter_end_price=52.0),
        _clean_row(quarter="2023Q3", quarter_end_price=48.0),
    ]
    df = pd.DataFrame(rows)
    assert len(rule_stale_price(df, min_consecutive=3)) == 0


def test_eps_reconciliation_catches_mismatch():
    # net_income/shares_out = 150/100 = 1.50, but reported EPS says 5.00
    df = pd.DataFrame([_clean_row(eps_reported=5.00)])
    flagged = rule_eps_reconciliation(df)
    assert len(flagged) == 1
    assert flagged.iloc[0]["exception_type"] == "EPS_RECONCILIATION_MISMATCH"


def test_eps_reconciliation_no_false_positive_within_tolerance():
    # 1.51 vs computed 1.50 is well within 2% tolerance
    df = pd.DataFrame([_clean_row(eps_reported=1.51)])
    assert len(rule_eps_reconciliation(df)) == 0


def test_run_all_rules_returns_expected_columns():
    df = pd.DataFrame([_clean_row(net_income_mm=np.nan)])
    result = run_all_rules(df)
    assert list(result.columns) == ["ticker", "quarter", "exception_type", "reason"]
    assert len(result) >= 1


if __name__ == "__main__":
    # Fallback runner for environments without pytest installed --
    # executes every test_* function and reports pass/fail without
    # requiring the pytest package. `pytest tests/ -v` is still the
    # normal way to run this file.
    import traceback
    tests = [(name, obj) for name, obj in list(globals().items())
              if name.startswith("test_") and callable(obj)]
    passed, failed = 0, 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
            passed += 1
        except Exception:
            print(f"FAIL  {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
