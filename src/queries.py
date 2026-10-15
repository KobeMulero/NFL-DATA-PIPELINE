import sqlite3

import pandas as pd

DB_PATH = "data/nfl.db"

QUERY = """
SELECT rusher_player_name AS player,
       posteam            AS team,
       carries,
       yards,
       yards_per_carry
FROM rushing
WHERE carries >= 150
ORDER BY yards DESC
LIMIT 10;
"""
RAVENS_RECEIVERS = """
SELECT receiver_player_name AS player, 
    targets,
    receptions,
    yards,
    catch_rate
From receiving 
WHERE posteam = 'BAL' AND targets >= 20
ORDER by catch_rate DESC
"""


with sqlite3.connect(DB_PATH) as conn:
    print(pd.read_sql(QUERY, conn).to_string(index=False))
    print()
    print(pd.read_sql(RAVENS_RECEIVERS, conn).to_string(index=False))