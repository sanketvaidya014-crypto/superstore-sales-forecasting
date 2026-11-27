"""Shared paths and helpers."""
import pathlib
import sqlite3

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "superstore.db"
SQL_DIR, OUT = ROOT / "sql", ROOT / "outputs"
FIG, TAB = OUT / "figures", OUT / "tables"
for _d in (RAW, FIG, TAB):
    _d.mkdir(parents=True, exist_ok=True)


def run_all_sql() -> dict:
    """Run every file in sql/, save each result to outputs/tables/<name>.csv, return DataFrames by name."""
    out = {}
    with sqlite3.connect(DB) as con:
        for f in sorted(SQL_DIR.glob("*.sql")):
            df = pd.read_sql_query(f.read_text(), con)
            df.to_csv(TAB / f"{f.stem}.csv", index=False)
            out[f.stem] = df
    return out


def load_sales() -> pd.DataFrame:
    with sqlite3.connect(DB) as con:
        return pd.read_sql_query("SELECT * FROM sales", con, parse_dates=["order_date", "ship_date"])
