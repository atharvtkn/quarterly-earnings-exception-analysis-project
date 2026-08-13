# Quarterly Earnings & Exception-Analysis Pipeline

A Python-based financial-data pipeline designed to demonstrate automated
exception analysis on quarterly company financial data.

The project ingests quarterly financial and market data for a basket of
companies, stores the data in SQLite, applies six automated exception-detection
rules, and produces flagged-record reports and diagnostic visualizations.

## What it does

1. Ingests quarterly financial and market data for 18 companies.
2. Standardizes the data into a common 9-field schema.
3. Stores the dataset in a local SQLite database.
4. Runs six independent exception-detection rules.
5. Outputs flagged exceptions as a CSV.
6. Generates a company × exception-type heatmap.
7. Generates company-level trend charts for flagged companies.

## Data schema

Each row represents one company-quarter observation.

The standardized dataset contains:

| Field | Description |
|---|---|
| `ticker` | Company/ticker identifier |
| `quarter` | Financial reporting quarter |
| `revenue_mm` | Revenue, in millions |
| `net_income_mm` | Net income, in millions |
| `total_equity_mm` | Total shareholders' equity, in millions |
| `total_assets_mm` | Total assets, in millions |
| `shares_out_mm` | Shares outstanding, in millions |
| `eps_reported` | Reported EPS |
| `quarter_end_price` | Approximate quarter-end market price |

## Exception rules

| Rule | What it checks |
|---|---|
| `MISSING_FIELD` | Missing required financial fields |
| `DUPLICATE_ROW` | Duplicate company-quarter records |
| `YOY_GROWTH_OUTLIER` | Revenue YoY growth that is unusually far outside the company's historical pattern |
| `NEGATIVE_EQUITY_OR_REVENUE` | Negative equity or revenue values |
| `STALE_PRICE_FEED` | Unchanged price across consecutive quarters, indicating a possible stale feed |
| `EPS_RECONCILIATION_MISMATCH` | Reported EPS that does not reconcile with an independently calculated EPS proxy |

An exception is a **flag for investigation**, not necessarily proof that the underlying
financial data is incorrect.

## Data sources

### Live data

`fetch_data_live.py` uses `yfinance` to retrieve:

- quarterly financial statements
- quarterly balance-sheet data
- historical market prices

The retrieved information is transformed into the standardized 9-field schema.

The live ingestion layer is intentionally kept separate from the analysis
pipeline so that the same exception-detection logic can be applied to the
resulting dataset.

### Synthetic data

`generate_data.py` creates a deterministic synthetic dataset for reproducible
testing.

The synthetic dataset contains deliberately planted issues, including:

- missing financial fields
- duplicate records
- abnormal revenue growth
- negative equity
- stale prices
- EPS reconciliation discrepancies

This allows the exception rules to be tested against known cases without
depending on external data availability.

## Pipeline architecture

```text
                    Data ingestion
                          |
             +------------+------------+
             |                         |
       Synthetic data              Live data
      generate_data.py          fetch_data_live.py
             |                         |
             +------------+------------+
                          |
                    Standardized
                    DataFrame
                          |
                          v
                    SQLite warehouse
                       db.py
                          |
                          v
                 Exception detection
                    exceptions.py
                          |
                          v
                  Flagged exceptions
                          |
                +---------+---------+
                |                   |
                v                   v
        exceptions_flagged.csv   Visualizations
                                  heatmap + charts
```

## Project structure

```text
earnings-exception-pipeline/
│
├── generate_data.py          # reproducible synthetic dataset generator
├── fetch_data_live.py        # live yfinance ingestion
├── db.py                     # SQLite warehouse layer
├── exceptions.py             # exception-detection rules
├── pipeline.py               # main pipeline/orchestrator
├── tests/
│   └── test_exceptions.py    # unit tests for exception rules
├── memo.md                   # research memo / investigation notes
├── requirements.txt
├── data/
└── output/
```

## Running the project

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the pipeline:

```bash
python pipeline.py
```

The pipeline will:

```text
fetch data
    ↓
load data into SQLite
    ↓
run six exception rules
    ↓
write flagged exceptions
    ↓
generate visualizations
```

The generated artifacts are written to `output/`.

## Live data ingestion

The live ingestion script can also be run independently:

```bash
python fetch_data_live.py
```

This retrieves the currently available quarterly data from the configured
companies and writes the standardized raw dataset.
