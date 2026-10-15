import html
import sqlite3
import textwrap

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = "data/nfl.db"

st.set_page_config(page_title="NFL Player Stats", page_icon="🏈", layout="wide")


@st.cache_data
def run_query(sql, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(sql, conn, params=params)


def brightness(hex_color):
    """How light a color is, from 0 (black) to 1 (white)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def apply_team_theme(primary, secondary):
    # Team color at the top, fading to near-black so white text stays readable
    css = textwrap.dedent(f"""
        <style>
        .stApp {{
            background: linear-gradient(170deg, {primary} 0%, {primary} 18%, #0E0E12 70%);
        }}
        .player-card {{
            background: rgba(255, 255, 255, 0.08);
            border-top: 4px solid {secondary};
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        }}
        .player-card img {{
            width: 140px;
            height: 140px;
            object-fit: cover;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.12);
        }}
        .player-card .name {{ font-size: 1.25rem; font-weight: 700; margin-top: 8px; }}
        .player-card .meta {{ opacity: 0.75; font-size: 0.9rem; }}
        .player-card .stat {{ font-size: 1.6rem; font-weight: 700; margin-top: 6px; }}
                .player-card .stat {{ font-size: 1.6rem; font-weight: 700; margin-top: 6px; }}
        .player-card {{
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .player-card:hover {{
            transform: translateY(-6px);
            box-shadow: 0 10px 30px {secondary}55;
        }}
        .stTabs [aria-selected="true"] {{ color: {secondary}; }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: {secondary}; }}
         </style>
    """)
    st.markdown(css, unsafe_allow_html=True)


def player_card(column, title, df):
    if df.empty:
        column.markdown(f"<div class='player-card'><div class='meta'>{title}</div>—</div>",
                        unsafe_allow_html=True)
        return
    row = df.iloc[0]
    name = html.escape(row["full_name"])  # handles names like Ja'Marr Chase
    photo = row["headshot"] if isinstance(row["headshot"], str) else ""
    jersey = f"#{int(row['jersey_number'])} · " if pd.notna(row["jersey_number"]) else ""
    position = row["position"] if isinstance(row["position"], str) else ""
    # Built line by line with no indentation: indented HTML gets shown as code
    parts = [
        "<div class='player-card'>",
        f"<div class='meta'>{title}</div>",
        f'<img src="{photo}" alt="{name}">' if photo else "",
        f"<div class='name'>{name}</div>",
        f"<div class='meta'>{jersey}{position}</div>",
        f"<div class='stat'>{row['yards']:,} yds</div>",
        f"<div class='meta'>#{int(row['nfl_rank'])} in the NFL</div>",
        "</div>",
    ]
    column.markdown("".join(parts), unsafe_allow_html=True)


def show_table(df):
    hidden = ["player_id", "posteam", "player", "headshot", "jersey_number"]
    table = df.drop(columns=hidden)
    first = ["full_name", "position"]
    table = table[first + [c for c in table.columns if c not in first]]
    st.dataframe(table.rename(columns={"full_name": "player"}), hide_index=True)


def ranked_query(table, id_col, name_col, columns, min_filter, team):
    # RANK() ranks every player in the NFL, then we keep only this team's players.
    # LEFT JOIN adds full names and headshots from the players table.
    sql = f"""
    SELECT s.*, COALESCE(p.display_name, s.player) AS full_name,
           p.position, p.jersey_number, p.headshot
    FROM (
        SELECT {id_col} AS player_id, {name_col} AS player, posteam, {columns},
               RANK() OVER (ORDER BY yards DESC) AS nfl_rank
        FROM {table}
    ) AS s
    LEFT JOIN players AS p ON p.gsis_id = s.player_id
    WHERE s.posteam = ? AND {min_filter}
    ORDER BY s.yards DESC
    """
    return run_query(sql, (team,))


def bar_chart(df, color):
    return (
        alt.Chart(df)
        .mark_bar(color=color, cornerRadiusEnd=4)
        .encode(
            x=alt.X("yards:Q", title="Yards", axis=alt.Axis(grid=True, gridOpacity=0.15)),
            y=alt.Y("full_name:N", sort="-x", title=None),
            tooltip=["full_name", "yards", "nfl_rank"],
        )
        .properties(height=max(120, 32 * len(df)))
        .configure(background="transparent")
    )

def clutch_table(team, situation, role):
    # Self-join: compare each player's stats in this situation to their own "All plays" numbers
    sql = """
    SELECT COALESCE(p.display_name, s.player_name) AS player,
           s.plays, s.yards, s.touchdowns, s.interceptions,
           s.first_down_rate, s.yards_per_play,
           ROUND(s.yards_per_play - a.yards_per_play, 1) AS vs_season
    FROM situational AS s
    JOIN situational AS a
      ON a.player_id = s.player_id AND a.role = s.role
     AND a.posteam = s.posteam AND a.situation = 'All plays'
    LEFT JOIN players AS p ON p.gsis_id = s.player_id
    WHERE s.posteam = ? AND s.situation = ? AND s.role = ? AND s.plays >= 5
    ORDER BY s.plays DESC
    """
    df = run_query(sql, (team, situation, role))
    if role != "Passing":
        df = df.drop(columns="interceptions")
    return df


# --- Sidebar ---
teams = run_query("""
    SELECT DISTINCT r.posteam, t.team_name, t.team_color, t.team_color2
    FROM rushing AS r
    JOIN teams AS t ON t.team_abbr = r.posteam
    ORDER BY t.team_name
""")
names = teams["team_name"].tolist()
with st.sidebar:
    st.header("Filters")
    team_name = st.selectbox("Team", names, index=names.index("Baltimore Ravens"))
    st.caption("Data: 2025 regular season play-by-play from nflverse. "
               "Stats rebuilt from individual plays and validated against official totals. "
               "Headshots via NFL.com.")

team_row = teams[teams["team_name"] == team_name].iloc[0]
team = team_row["posteam"]
primary, secondary = team_row["team_color"], team_row["team_color2"]
bar_color = secondary if brightness(secondary) > 0.25 else "#D9D9E3"
apply_team_theme(primary, secondary)

# --- Data ---
passing = ranked_query(
    "passing", "passer_player_id", "passer_player_name",
    "CAST(attempts AS INTEGER) AS attempts, CAST(completions AS INTEGER) AS completions, "
    "CAST(yards AS INTEGER) AS yards, CAST(touchdowns AS INTEGER) AS touchdowns, "
    "CAST(interceptions AS INTEGER) AS interceptions, comp_pct, yards_per_att",
    "attempts >= 10", team,
)
rushing = ranked_query(
    "rushing", "rusher_player_id", "rusher_player_name",
    "CAST(carries AS INTEGER) AS carries, CAST(yards AS INTEGER) AS yards, "
    "CAST(touchdowns AS INTEGER) AS touchdowns, yards_per_carry",
    "carries >= 10", team,
)
receiving = ranked_query(
    "receiving", "receiver_player_id", "receiver_player_name",
    "CAST(targets AS INTEGER) AS targets, CAST(receptions AS INTEGER) AS receptions, "
    "CAST(yards AS INTEGER) AS yards, CAST(touchdowns AS INTEGER) AS touchdowns, catch_rate",
    "targets >= 10", team,
)

# --- Header and top players ---
st.title(team_name)
st.caption("2025 NFL regular season")

col1, col2, col3 = st.columns(3)
player_card(col1, "Passing leader", passing)
player_card(col2, "Rushing leader", rushing)
player_card(col3, "Receiving leader", receiving)

st.write("")

# --- Tabs ---
tab_rush, tab_rec, tab_pass, tab_clutch = st.tabs(["Rushing", "Receiving", "Passing", "Clutch stats"])

with tab_rush:
    st.altair_chart(bar_chart(rushing, bar_color))
    show_table(rushing)

with tab_rec:
    st.altair_chart(bar_chart(receiving, bar_color))
    show_table(receiving)

with tab_pass:
    show_table(passing)
    
with tab_clutch:
    situation = st.radio(
        "Situation",
        ["3rd down", "Red zone", "4th quarter", "Clutch (4th Q or OT, within 8 pts)"],
        horizontal=True,
    )
    st.caption("vs_season = yards per play in this situation minus the player's season average. "
               "Green means better when it matters. Players with at least 5 plays shown.")
    if situation == "Red zone":
        st.info("In the red zone the field is short, so yards per play is lower for everyone. "
                "Touchdowns are the stat that matters here.")
    for role in ["Passing", "Rushing", "Receiving"]:
        df = clutch_table(team, situation, role)
        st.subheader(role)
        if df.empty:
            st.write("Not enough plays in this situation.")
            continue
        st.dataframe(
            df.style.map(
                lambda v: f"color: {'#4ADE80' if v > 0 else '#F87171' if v < 0 else 'inherit'}",
                subset=["vs_season"],
            ).format({"vs_season": "{:+.1f}", "first_down_rate": "{:.1f}%", "yards_per_play": "{:.1f}"}),
            hide_index=True,
        )