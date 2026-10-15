import pandas as pd

df = pd.read_csv("data/raw/pbp_2025.csv.gz", low_memory=False)
print(df.shape)  # (rows, columns)

ravens = df[df["posteam"] == "BAL"]  # plays where the Ravens had the ball

print("\nTop passers:")
print(ravens["passer_player_name"].value_counts().head(3))
print("\nTop rushers:")
print(ravens["rusher_player_name"].value_counts().head(3))
print("\nTop receivers (by targets):")
print(ravens["receiver_player_name"].value_counts().head(3))