"""Clean the Superstore CSV and load it into SQLite (data/superstore.db, table `sales`)."""
import sqlite3

import pandas as pd

from common import DB, RAW

CANDIDATES = ["Sample - Superstore.csv", "SampleSuperstore.csv", "Superstore.csv", "train.csv"]
REQUIRED = ["order_id", "order_date", "ship_date", "customer_id", "segment", "region", "state", "city", "product_id",
            "category", "sub_category", "product_name", "sales", "quantity", "discount", "profit"]


def read_any(path):
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"Could not decode {path}")


def parse_dates(s: pd.Series) -> pd.Series:
    """Superstore exports use m/d/Y or d/m/Y depending on the source; try strict formats first."""
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(s)


def main() -> None:
    src = next((RAW / f for f in CANDIDATES if (RAW / f).exists()), None)
    if src is None:
        raise SystemExit(f"No dataset found in {RAW}.\nDownload the Superstore Sales CSV from Kaggle and save it as "
                         f"'{CANDIDATES[0]}', or run `python src/make_sample_data.py` for a synthetic demo file.")
    df = read_any(src)
    df.columns = (df.columns.str.strip().str.lower().str.replace(r"[\s\-]+", "_", regex=True))
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing columns {missing}. Found: {list(df.columns)}")

    n0 = len(df)
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "row_id"])
    for c in ("order_date", "ship_date"):
        df[c] = parse_dates(df[c]).dt.strftime("%Y-%m-%d")
    for c in ("sales", "quantity", "discount", "profit"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    bad = df[["order_date", "sales", "profit", "discount"]].isna().any(axis=1).sum()
    df = df.dropna(subset=["order_date", "sales", "profit"])
    months = pd.PeriodIndex(df.order_date.str[:7], freq="M")
    gaps = len(pd.period_range(months.min(), months.max())) - months.nunique()

    if DB.exists():
        DB.unlink()
    with sqlite3.connect(DB) as con:
        df.to_sql("sales", con, index=False)
        con.execute("CREATE INDEX ix_sales_date ON sales(order_date)")
    print(f"Source: {src.name}\nRows: {n0:,} read, {n0 - len(df):,} dropped (duplicates / invalid)\n"
          f"Date range: {df.order_date.min()} to {df.order_date.max()}  | missing months: {gaps}\n"
          f"Discount range: {df.discount.min():.2f}-{df.discount.max():.2f} (expected 0-1)  | "
          f"loss-making lines: {(df.profit < 0).mean():.1%}  | invalid values removed: {bad}\nDatabase ready: {DB}")


if __name__ == "__main__":
    main()
