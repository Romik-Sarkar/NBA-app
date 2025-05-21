from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguestandings
import pandas as pd

# Get all NBA teams
nba_teams = teams.get_teams()
team_info_df = pd.DataFrame(nba_teams)[['id', 'full_name', 'abbreviation']]

# Get current league standings
standings_df = leaguestandings.LeagueStandings(season='2024-25').get_data_frames()[0]

# Select and rename relevant columns
standings = standings_df[['TeamID', 'TeamName', 'Conference', 'PlayoffRank', 'WINS', 'LOSSES', 'WinPCT']]
standings = standings.rename(columns={
    'TeamID': 'id',
    'PlayoffRank': 'ConferenceRank',
    'WinPCT': 'WinPercentage'
})

# Merge with team info to get full names and abbreviations
merged_df = pd.merge(team_info_df, standings, on='id')

# Sort by Conference and ConferenceRank
merged_df = merged_df.sort_values(by=['Conference', 'ConferenceRank'])

# Clean display
print(merged_df[['full_name', 'abbreviation', 'Conference', 'ConferenceRank', 'WINS', 'LOSSES', 'WinPercentage']].to_string(index=False))