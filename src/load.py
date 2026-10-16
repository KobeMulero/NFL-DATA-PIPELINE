import sqlite3
from pathlib import Path

import pandas as pd
from config import SEASONS

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
DB_PATH = Path("data/nfl.db")


def load_table(conn, name):
    frames = []
    for season in SEASONS:
        season_df = pd.read_csv(PROCESSED_DIR / f"{name}_{season}.csv")
        season_df["season"] = season
        frames.append(season_df)
    df = pd.concat(frames, ignore_index=True)  # stack all seasons into one table
    df.to_sql(name, conn, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into '{name}'")


def load_players(conn):
    cols = ["gsis_id", "display_name", "position", "jersey_number", "headshot"]
    df = pd.read_csv(RAW_DIR / "players.csv", usecols=cols, low_memory=False)
    df = df.dropna(subset=["gsis_id"])
    df.to_sql("players", conn, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into 'players'")


def load_teams(conn):
    cols = ["team_abbr", "team_name", "team_color", "team_color2"]
    df = pd.read_csv(RAW_DIR / "teams.csv", usecols=cols)
    df.to_sql("teams", conn, if_exists="replace", index=False)
    print(f"Loaded {len(df)} rows into 'teams'")


def main():
    with sqlite3.connect(DB_PATH) as conn:
        for name in ["passing", "rushing", "receiving", "situational"]:
            load_table(conn, name)
        load_players(conn)
        load_teams(conn)


if __name__ == "__main__":
    main()