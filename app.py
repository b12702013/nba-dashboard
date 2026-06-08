import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import requests
from nba_api.stats.endpoints import leaguegamelog
from data_pipeline import run_pipeline
from datetime import datetime, timedelta
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.static import teams




DB_NAME = "nba_data.db"


def load_data():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM player_stats", conn)
    conn.close()
    return df

def load_update_time():
    conn = sqlite3.connect(DB_NAME)

    try:
        update_df = pd.read_sql("SELECT * FROM update_log", conn)
        last_updated = update_df["last_updated"].iloc[0]
    except:
        last_updated = "Not updated yet"

    conn.close()
    return last_updated

def get_team_abbreviation(team_id):
    """
    Convert NBA team ID to team abbreviation.
    """
    all_teams = teams.get_teams()

    for team in all_teams:
        if team["id"] == team_id:
            return team["abbreviation"]

    return "Unknown"

def get_next_game():
    """
    Search for upcoming NBA games from NBA schedule JSON.
    """
    urls = [
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.nba.com/schedule"
    }

    try:
        for url in urls:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                continue

            data = response.json()

            games_list = []

            for game_date_group in data["leagueSchedule"]["gameDates"]:
                for game in game_date_group["games"]:
                    game_time = pd.to_datetime(game["gameDateTimeUTC"], utc=True)

                    if game_time > pd.Timestamp.now(tz="UTC"):
                        away_team = game["awayTeam"]["teamTricode"]
                        home_team = game["homeTeam"]["teamTricode"]

                        games_list.append({
                            "game_time": game_time,
                            "away_team": away_team,
                            "home_team": home_team
                        })

            if len(games_list) > 0:
                games_df = pd.DataFrame(games_list)
                games_df = games_df.sort_values(by="game_time")


                next_game = games_df.iloc[0]

                game_time_taiwan = next_game["game_time"].tz_convert("Asia/Taipei")
                game_time_display = game_time_taiwan.strftime("%Y-%m-%d %H:%M")
                game_time_display = f"{game_time_display} Taiwan Time"

                return game_time_display, next_game["away_team"], next_game["home_team"]

    except Exception as e:
        st.write("Schedule JSON error:", e)

    return None, None, None

st.sidebar.title("Dashboard Info")

st.sidebar.write("**Dataset:** 2025-26 NBA Playoffs")
st.sidebar.write("**Data Source:** NBA API")
st.sidebar.write("**Database:** SQLite")
st.sidebar.write("**Refresh Method:** Update Data button")

st.sidebar.markdown("---")

st.sidebar.write("**Main Features:**")
st.sidebar.write("- Player rankings")
st.sidebar.write("- Player search")
st.sidebar.write("- Player comparison")
st.sidebar.write("- Remaining teams filter")
st.sidebar.write("- Next game schedule")
st.title("NBA Player Statistics Dashboard")

st.write("This dashboard shows NBA player statistics from a SQLite database.")

if st.button("Update Data"):
    try:
        with st.spinner("Updating NBA data..."):
            run_pipeline()
        st.success("Data updated successfully!")
    except Exception as e:
        st.error("Update failed because the NBA API did not respond in time. Please try again later.")
        st.info("The dashboard will continue using the most recently saved data.")
df = load_data()

last_updated = load_update_time()
st.caption(f"Last Updated: {last_updated}")
game_date, away_team, home_team = get_next_game()

st.subheader("Next NBA Game")

if game_date is not None:
    st.info(f"{away_team} @ {home_team} — {game_date}")
else:
    st.warning("No upcoming NBA game found in the next 60 days.")
# Summary cards
st.subheader("Remaining Playoff Teams")

remaining_east = ["NYK"]
remaining_west = ["SAS"]

remaining_teams = remaining_east + remaining_west

show_remaining_only = st.checkbox("Show only remaining teams")

col1, col2 = st.columns(2)

with col1:
    st.write("**Eastern Conference**")
    for team in remaining_east:
        st.write(f"- {team}")

with col2:
    st.write("**Western Conference**")
    for team in remaining_west:
        st.write(f"- {team}")
if show_remaining_only:
    df = df[df["TEAM_ABBREVIATION"].isin(remaining_teams)]

total_players = len(df)
total_teams = df["TEAM_ABBREVIATION"].nunique()

col1, col2 = st.columns(2)

col1.metric("Total Players", total_players)
col2.metric("Total Teams", total_teams)

st.subheader("Top 10 Scorers")

top_scorers = df.sort_values(by="PPG", ascending=False).head(10)

fig = px.bar(
    top_scorers,
    x="PLAYER_NAME",
    y="PPG",
    title="Top 10 NBA Players by Points Per Game",
    labels={
        "PLAYER_NAME": "Player",
        "PPG": "Points Per Game"
    }
)
st.plotly_chart(fig, use_container_width=True)
st.subheader("Top 10 Rebounders")

top_rebounders = df.sort_values(by="RPG", ascending=False).head(10)

fig_reb = px.bar(
    top_rebounders,
    x="PLAYER_NAME",
    y="RPG",
    title="Top 10 NBA Players by Rebounds Per Game",
    labels={
        "PLAYER_NAME": "Player",
        "RPG": "Rebounds Per Game"
    }
)

st.plotly_chart(fig_reb, use_container_width=True)
st.subheader("Top 10 Assists")

top_assists = df.sort_values(by="APG", ascending=False).head(10)

fig_ast = px.bar(
    top_assists,
    x="PLAYER_NAME",
    y="APG",
    title="Top 10 NBA Players by Assists Per Game",
    labels={
        "PLAYER_NAME": "Player",
        "APG": "Assists Per Game"
    }
)


st.plotly_chart(fig_ast, use_container_width=True)
st.subheader("Player Search")

selected_player = st.selectbox(
    "Select a player",
    df["PLAYER_NAME"].sort_values()
)

player_data = df[df["PLAYER_NAME"] == selected_player].iloc[0]

st.write(f"### {selected_player}")

col1, col2, col3 = st.columns(3)

col1.metric("Points", int(player_data["PTS"]))
col2.metric("Rebounds", int(player_data["REB"]))
col3.metric("Assists", int(player_data["AST"]))

col4, col5, col6 = st.columns(3)

col4.metric("FG%", f"{player_data['FG_PCT']:.3f}")
col5.metric("3P%", f"{player_data['FG3_PCT']:.3f}")
col6.metric("Performance Score", int(player_data["PERFORMANCE_SCORE"]))
st.subheader("Player Comparison")

player_list = df["PLAYER_NAME"].sort_values()

player_a = st.selectbox("Select Player A", player_list, index=0)
player_b = st.selectbox("Select Player B", player_list, index=1)

comparison_df = df[df["PLAYER_NAME"].isin([player_a, player_b])]

comparison_stats = comparison_df[
    ["PLAYER_NAME", "PTS", "REB", "AST", "STL", "BLK", "PERFORMANCE_SCORE"]
]

comparison_melted = comparison_stats.melt(
    id_vars="PLAYER_NAME",
    var_name="Statistic",
    value_name="Value"
)

fig_compare = px.bar(
    comparison_melted,
    x="Statistic",
    y="Value",
    color="PLAYER_NAME",
    barmode="group",
    title=f"{player_a} vs {player_b}",
    labels={
        "PLAYER_NAME": "Player",
        "Value": "Value"
    }
)

st.plotly_chart(fig_compare, use_container_width=True)
with st.expander("Show Raw Data"):
    st.dataframe(df)
