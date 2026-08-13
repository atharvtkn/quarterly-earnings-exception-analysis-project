"""
db.py
-----
SQLite warehouse layer.
"""

import sqlite3
from pathlib import Path
import pandas as pd


# Always resolve the database relative to this project's folder.
PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "output"
DB_PATH = OUTPUT_DIR / "warehouse.db"


def load_to_sqlite(
    df: pd.DataFrame,
    db_path=DB_PATH,
    table: str = "quarterly_financials"
):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        df.to_sql(table, conn, if_exists="replace", index=False)
    finally:
        conn.close()


def read_from_sqlite(
    db_path=DB_PATH,
    table: str = "quarterly_financials"
) -> pd.DataFrame:
    db_path = Path(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        return pd.read_sql(f"SELECT * FROM {table}", conn)
    finally:
        conn.close()