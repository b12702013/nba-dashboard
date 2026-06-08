import sqlite3
import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats
from datetime import datetime
from zoneinfo import ZoneInfo

DB_NAME = "nba_data.db"


def fetch_nba_player_stats(season="2025-26"):
    """
    Fetch NBA player season statistics from nba_api.
    """
    stats = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        season_type_all_star="Playoffs"
    )
    df = stats.get_data_frames()[0]
    return df


def clean_player_stats(df):
    """
    Clean and transform raw NBA player statistics.
    """
    columns = [
        "PLAYER_NAME", "TEAM_ABBREVIATION", "GP", "MIN",
        "PTS", "REB", "AST", "STL", "BLK", "TOV",
        "FG_PCT", "FG3_PCT", "FT_PCT"
    ]

    df = df[columns].copy()
    df["PPG"] = (df["PTS"] / df["GP"]).round(1)
    df["RPG"] = (df["REB"] / df["GP"]).round(1)
    df["APG"] = (df["AST"] / df["GP"]).round(1)

    df["PERFORMANCE_SCORE"] = (
        df["PTS"] + df["REB"] + df["AST"] + df["STL"] + df["BLK"] - df["TOV"]
    )

    return df


def save_to_database(df):
    """
    Save cleaned NBA player statistics into SQLite database.
    """
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("player_stats", conn, if_exists="replace", index=False)
    conn.close()

def save_update_time():
    """
    Save the latest data update time into SQLite database.
    """
    conn = sqlite3.connect(DB_NAME)

    update_df = pd.DataFrame({
        "last_updated": [datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S"))]
    })

    update_df.to_sql("update_log", conn, if_exists="replace", index=False)

    conn.close()


def run_pipeline():
    """
    Run the complete ETL pipeline:
    Extract -> Transform -> Load.
    """
    raw_df = fetch_nba_player_stats()
    clean_df = clean_player_stats(raw_df)
    save_to_database(clean_df)
    save_update_time()
    return clean_df


if __name__ == "__main__":
    df = run_pipeline()
    print("Data pipeline completed successfully.")
    print(df.head())
