import sqlite3
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path("data/processed")
DB_PATH = Path("data/nfl.db")
SEASON = 2025


def load_table(conn, name):
    df = pd.read_csv(PROCESSED_DIR / f"{name}_{SEASON}.csv")
    df["season"] = SEASON
    df.to_sql(name, conn, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into '{name}'")


if __name__ == "__main__":
    with sqlite3.connect(DB_PATH) as conn:
        for name in ["passing", "rushing", "receiving"]:
            load_table(conn, name)