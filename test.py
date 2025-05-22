import requests
import pandas as pd

def get_season_leaders(stat_category='PTS', season='2024-25', topx=10):
    url = "https://stats.nba.com/stats/leagueleaders"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com"
    }

    params = {
        "LeagueID": "00",
        "PerMode": "Totals",         # Other valid: PerGame, Per48
        "Scope": "S",                # 'S' = Season
        "Season": season,            # e.g., '2023-24'
        "SeasonType": "Regular Season",
        "StatCategory": stat_category,
        "ActiveFlag": ""             # Nullable; leave blank
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    result = response.json()['resultSet']
    headers = result['headers']
    rows = result['rowSet']
    
    df = pd.DataFrame(rows, columns=headers)
    return df.head(topx)

# Example usage
if __name__ == "__main__":
    leaders = get_season_leaders(stat_category='PTS', season='2023-24')
    print(leaders[['PLAYER', 'TEAM', 'PTS', 'GP']])
