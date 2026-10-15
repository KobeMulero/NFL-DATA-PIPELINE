import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def load_plays(season):
    df = pd.read_csv(RAW_DIR / f"pbp_{season}.csv.gz", low_memory=False)

    # Keep only real offensive plays from the regular season
    plays = df[
        (df["season_type"] == "REG")
        & (df["play_type"].isin(["pass", "run", "qb_kneel", "qb_spike"]))
        & (df["two_point_attempt"] == 0)
    ]
    return plays


def passing_stats(plays):
    passes = plays[(plays["pass_attempt"] == 1) & (plays["sack"] == 0)]
    stats = passes.groupby(["passer_player_id", "passer_player_name", "posteam"]).agg(
        attempts=("pass_attempt", "sum"),
        completions=("complete_pass", "sum"),
        yards=("passing_yards", "sum"),
        touchdowns=("pass_touchdown", "sum"),
        interceptions=("interception", "sum"),
    )
    stats["comp_pct"] = (stats["completions"] / stats["attempts"] * 100).round(1)
    stats["yards_per_att"] = (stats["yards"] / stats["attempts"]).round(1)
    return stats.reset_index().sort_values("yards", ascending=False)


def rushing_stats(plays):
    runs = plays[plays["rush_attempt"] == 1]
    stats = runs.groupby(["rusher_player_id", "rusher_player_name", "posteam"]).agg(
        carries=("rush_attempt", "sum"),
        yards=("rushing_yards", "sum"),
        touchdowns=("rush_touchdown", "sum"),
    )
    stats["yards_per_carry"] = (stats["yards"] / stats["carries"]).round(1)
    return stats.reset_index().sort_values("yards", ascending=False)


def receiving_stats(plays):
    targets = plays[(plays["pass_attempt"] == 1) & (plays["receiver_player_id"].notna())]
    stats = targets.groupby(["receiver_player_id", "receiver_player_name", "posteam"]).agg(
        targets=("pass_attempt", "sum"),
        receptions=("complete_pass", "sum"),
        yards=("receiving_yards", "sum"),
        touchdowns=("pass_touchdown", "sum"),
    )
    stats["catch_rate"] = (stats["receptions"] / stats["targets"] * 100).round(1)
    return stats.reset_index().sort_values("yards", ascending=False)


if __name__ == "__main__":
    season = 2025
    plays = load_plays(season)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    tables = {
        "passing": passing_stats(plays),
        "rushing": rushing_stats(plays),
        "receiving": receiving_stats(plays),
    }

    for name, table in tables.items():
        path = PROCESSED_DIR / f"{name}_{season}.csv"
        table.to_csv(path, index=False)
        print(f"Saved {path} ({len(table)} players)")

        ravens = table[table["posteam"] == "BAL"]
        print(ravens.head(3).to_string(index=False))
        print()