import sqlite3

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = "data/nfl.db"


@st.cache_data
def run_query(sql, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(sql, conn, params=params)


def bar_chart(df, value):
    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(value, title=value.replace("_", " ").title()),
            y=alt.Y("player", sort="-x", title=None),
            tooltip=list(df.columns),
        )
    )


st.title("NFL Player Stats Dashboard")
st.caption("Built from 2025 regular season play-by-play data (nflverse)")

teams = run_query("SELECT DISTINCT posteam FROM rushing ORDER BY posteam")["posteam"].tolist()
team = st.selectbox("Team", teams, index=teams.index("BAL"))

# Rushing
st.header(f"{team} Rushing")
rushing = run_query(
    """
    SELECT rusher_player_name AS player, carries, yards, touchdowns, yards_per_carry
    FROM rushing
    WHERE posteam = ? AND carries >= 10
    ORDER BY yards DESC
    """,
    (team,),
)
st.altair_chart(bar_chart(rushing, "yards"))
st.dataframe(rushing, hide_index=True)

# Receiving
st.header(f"{team} Receiving")
receiving = run_query(
    """
    SELECT receiver_player_name AS player, targets, receptions, yards, touchdowns, catch_rate
    FROM receiving
    WHERE posteam = ? AND targets >= 10
    ORDER BY yards DESC
    """,
    (team,),
)
st.altair_chart(bar_chart(receiving, "yards"))
st.dataframe(receiving, hide_index=True)

# Passing
st.header(f"{team} Passing")
passing = run_query(
    """
    SELECT passer_player_name AS player, attempts, completions, yards,
           touchdowns, interceptions, comp_pct, yards_per_att
    FROM passing
    WHERE posteam = ?
    ORDER BY attempts DESC
    """,
    (team,),
)
st.dataframe(passing, hide_index=True)
