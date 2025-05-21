from nba_api.stats.static import teams
from nba_api.stats.endpoints import commonteamroster, playergamelog
from nba_api.stats.library.parameters import SeasonType
import pandas as pd
import time

def get_team_id(team_name="Los Angeles Lakers"):
    nba_teams = teams.get_teams()
    team = [team for team in nba_teams if team['full_name'] == team_name][0]
    return team['id']

def get_team_roster(team_id, season='2024-25'):
    roster = commonteamroster.CommonTeamRoster(team_id=team_id, season=season)
    return roster.get_data_frames()[0]

def convert_min_to_float(min_str):
    # If min_str is a string with ':', convert MM:SS to float minutes
    if isinstance(min_str, str) and ':' in min_str:
        minutes, seconds = min_str.split(':')
        return int(minutes) + int(seconds) / 60
    try:
        # Otherwise, convert directly to float (for integer minute strings or ints)
        return float(min_str)
    except (ValueError, TypeError):
        return 0.0

def get_player_season_averages(player_id, team_id, season='2024-25'):
    try:
        # Get all player game logs for the season
        logs = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star=SeasonType.regular
        ).get_data_frames()[0]
        
        # The MATCHUP column contains team information like "LAL vs. DAL" or "LAL @ NYK"
        # We can use this to filter games where the player was on the Lakers
        
        # First, get the team abbreviation for our team_id
        nba_teams = teams.get_teams()
        team_abbr = next((team['abbreviation'] for team in nba_teams if team['id'] == team_id), None)
        
        if team_abbr is None:
            return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
        
        # Filter logs to only include games where player was on this team
        # MATCHUP format is either "TEAM vs. OPP" or "TEAM @ OPP" where TEAM is player's team
        team_logs = logs[logs['MATCHUP'].str.startswith(team_abbr)].copy()
        
        if team_logs.empty:
            return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
        
        gp = team_logs.shape[0]
        team_logs.loc[:, 'MIN_float'] = team_logs['MIN'].apply(convert_min_to_float)
        avg_min = team_logs['MIN_float'].mean()
        avg_pts = team_logs['PTS'].mean()
        avg_oreb = team_logs['OREB'].mean()
        avg_dreb = team_logs['DREB'].mean()
        avg_reb = team_logs['REB'].mean()
        avg_ast = team_logs['AST'].mean()
        avg_stl = team_logs['STL'].mean()
        avg_blk = team_logs['BLK'].mean()
        avg_to = team_logs['TOV'].mean()
        avg_pf = team_logs['PF'].mean()
        
        ast_to = avg_ast / avg_to if avg_to > 0 else 0
        
        return {
            'GP': gp,
            'MIN': round(avg_min, 1),
            'PTS': round(avg_pts, 1),
            'OREB': round(avg_oreb, 1),
            'DREB': round(avg_dreb, 1),
            'REB': round(avg_reb, 1),
            'AST': round(avg_ast, 1),
            'STL': round(avg_stl, 1),
            'BLK': round(avg_blk, 1),
            'TO': round(avg_to, 1),
            'PF': round(avg_pf, 1),
            'AST_TO': round(ast_to, 2)
        }
    except Exception as e:
        print(f"Error getting stats for player ID {player_id}: {e}")
        return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
    
if __name__ == "__main__":
    team_id = get_team_id()
    roster_df = get_team_roster(team_id)

    print("🟨 Lakers Roster 2024-25 with Season Averages:")
    roster_with_stats = []

    for _, player in roster_df.iterrows():
        player_id = player['PLAYER_ID']
        player_name = player['PLAYER']
        stats = get_player_season_averages(player_id, team_id)
        roster_with_stats.append({
            'PLAYER': player_name,
            'NUM': player['NUM'],
            'POSITION': player['POSITION'],
            'HEIGHT': player['HEIGHT'],
            'WEIGHT': player['WEIGHT'],
            **stats
        })
        time.sleep(0.6)  # avoid rate limit

    df = pd.DataFrame(roster_with_stats)
    print(df[['PLAYER', 'NUM', 'POSITION', 'HEIGHT', 'WEIGHT', 'GP', 'MIN', 'PTS', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TO', 'PF', 'AST_TO']])