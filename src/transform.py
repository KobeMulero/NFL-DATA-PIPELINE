import pandas as pd
from pathlib import Path
from config import SEASONS

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

# Only the columns we use: reading 26 of 372 columns uses far less memory
COLUMNS = [
    "season_type", "play_type", "two_point_attempt", "posteam",
    "down", "qtr", "yardline_100", "score_differential",
    "pass_attempt", "sack", "complete_pass", "interception", "pass_touchdown", "first_down_pass",
    "passer_player_id", "passer_player_name", "passing_yards",
    "receiver_player_id", "receiver_player_name", "receiving_yards",
    "rush_attempt", "rush_touchdown", "first_down_rush",
    "rusher_player_id", "rusher_player_name", "rushing_yards",
]

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

SITUATIONS = {
    "All plays": lambda p: pd.Series(True, index=p.index),
    "3rd down": lambda p: p["down"] == 3,
    "Red zone": lambda p: p["yardline_100"] <= 20,
    "4th quarter": lambda p: p["qtr"] == 4,
    "Clutch (4th Q or OT, within 8 pts)": lambda p: (p["qtr"] >= 4) & (p["score_differential"].abs() <= 8),
}


def situational_stats(plays):
    # Kneels and spikes aren't real attempts to gain yards, so leave them out here
    real = plays[plays["play_type"].isin(["pass", "run"])]

    passes = real[(real["pass_attempt"] == 1) & (real["sack"] == 0)]
    runs = real[real["rush_attempt"] == 1]
    targets = passes[passes["receiver_player_id"].notna()]

    # One row per player per play, in the same shape for every role
    roles = [
        ("Passing", passes, "passer_player_id", "passer_player_name", "passing_yards", "pass_touchdown", "first_down_pass"),
        ("Rushing", runs, "rusher_player_id", "rusher_player_name", "rushing_yards", "rush_touchdown", "first_down_rush"),
        ("Receiving", targets, "receiver_player_id", "receiver_player_name", "receiving_yards", "pass_touchdown", "first_down_pass"),
    ]

    frames = []
    for role, df, id_col, name_col, yards_col, td_col, fd_col in roles:
        for situation, condition in SITUATIONS.items():
            subset = df[condition(df)]
            stats = subset.groupby([id_col, name_col, "posteam"]).agg(
                plays=(id_col, "size"),
                yards=(yards_col, "sum"),
                touchdowns=(td_col, "sum"),
                first_downs=(fd_col, "sum"),
                interceptions=("interception", "sum"),
            ).reset_index()
            stats.columns = ["player_id", "player_name", "posteam"] + list(stats.columns[3:])
            stats["role"] = role
            stats["situation"] = situation
            frames.append(stats)

    result = pd.concat(frames, ignore_index=True)
    result["yards_per_play"] = (result["yards"] / result["plays"]).round(1)
    result["first_down_rate"] = (result["first_downs"] / result["plays"] * 100).round(1)
    count_cols = ["plays", "yards", "touchdowns", "first_downs", "interceptions"]
    result[count_cols] = result[count_cols].astype(int)
    return result


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for season in SEASONS:
        plays = load_plays(season)
        tables = {
            "passing": passing_stats(plays),
            "rushing": rushing_stats(plays),
            "receiving": receiving_stats(plays),
            "situational": situational_stats(plays),
        }
        for name, table in tables.items():
            path = PROCESSED_DIR / f"{name}_{season}.csv"
            table.to_csv(path, index=False)
            print(f"Saved {path} ({len(table)} rows)")


if __name__ == "__main__":
    main()