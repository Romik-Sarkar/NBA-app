from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguestandings
import pandas as pd
import json

def test_standings_api():
    print("Testing NBA standings API...")
    try:
        # Get all NBA teams
        nba_teams = teams.get_teams()
        team_info_df = pd.DataFrame(nba_teams)[['id', 'full_name', 'abbreviation']]
        print(f"Loaded {len(nba_teams)} NBA teams")
        
        # Get current league standings
        standings = leaguestandings.LeagueStandings().get_data_frames()[0]
        print(f"Loaded standings data with {len(standings)} rows")
        
        # Print standings columns for reference
        print("\nAvailable columns in standings data:")
        print(standings.columns.tolist())
        
        # Select and rename relevant columns
        standings_data = standings[['TeamID', 'TeamName', 'Conference', 'PlayoffRank', 'WINS', 'LOSSES', 'WinPCT']]
        standings_data = standings_data.rename(columns={
            'TeamID': 'id',
            'PlayoffRank': 'ConferenceRank',
            'WinPCT': 'WinPercentage'
        })
        
        # Print info after renaming
        print("\nAfter selecting and renaming columns:")
        print(standings_data.columns.tolist())
        
        # Print samples of data before merging
        print("\nSample team info:")
        print(team_info_df.head(3))
        
        print("\nSample standings data:")
        print(standings_data.head(3))
        
        # Try both merging approaches for comparison
        print("\n=== Testing different merge methods ===")
        
        # Original approach from app.py
        original_df = pd.merge(standings_data, team_info_df, on='id', how='left')
        print("\nOriginal approach (app.py) - standings LEFT JOIN team_info:")
        print(f"Resulting rows: {len(original_df)}")
        print(original_df.columns.tolist())
        print(original_df.head(3))
        
        # Approach from test.py
        test_df = pd.merge(team_info_df, standings_data, on='id')
        print("\ntest.py approach - team_info INNER JOIN standings:")
        print(f"Resulting rows: {len(test_df)}")
        print(test_df.columns.tolist())
        print(test_df.head(3))
        
        # Modified approach with inner join
        modified_df = pd.merge(standings_data, team_info_df, on='id', how='inner')
        print("\nModified approach - standings INNER JOIN team_info:")
        print(f"Resulting rows: {len(modified_df)}")
        print(modified_df.columns.tolist())
        print(modified_df.head(3))
        
        # Sort and convert to JSON for final output
        modified_df = modified_df.sort_values(by=['Conference', 'ConferenceRank'])
        standings_list = modified_df.to_dict('records')
        
        # Check data format for specific keys needed by frontend
        print("\nChecking required fields in first record:")
        first_record = standings_list[0] if standings_list else {}
        required_fields = ['id', 'full_name', 'abbreviation', 'Conference', 'ConferenceRank', 'WINS', 'LOSSES', 'WinPercentage']
        for field in required_fields:
            present = field in first_record
            print(f"{field}: {'✓ Present' if present else '✗ Missing'}")
        
        # Print final JSON sample
        print("\nFinal JSON sample (first 3 records):")
        print(json.dumps(standings_list[:3], indent=2))
        
        # Count teams by conference
        east = [t for t in standings_list if t['Conference'] == 'East' or t['Conference'] == 'Eastern']
        west = [t for t in standings_list if t['Conference'] == 'West' or t['Conference'] == 'Western']
        print(f"\nTeams by conference: East={len(east)}, West={len(west)}")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        import traceback
        print(f"Error in test script: {str(e)}")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_standings_api()