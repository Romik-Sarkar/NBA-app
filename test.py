from nba_api.stats.endpoints import scoreboardv2
import time

time.sleep(1.5)

game_date = '05/20/2025'

try:
    scoreboard = scoreboardv2.ScoreboardV2(game_date=game_date)

    game_headers = scoreboard.get_data_frames()[0]  # GameHeader
    linescores = scoreboard.get_data_frames()[1]    # LineScore

    if game_headers.empty:
        print(f"📭 No NBA games found on {game_date}.")
    else:
        print(f"🏀 NBA Games on {game_date}:")

        for _, game in game_headers.iterrows():
            home_team_id = game['HOME_TEAM_ID']
            visitor_team_id = game['VISITOR_TEAM_ID']
            game_status = game['GAME_STATUS_TEXT']  # e.g. "Scheduled", "Final"

            # Get team names from LineScore
            home_team = linescores[linescores['TEAM_ID'] == home_team_id]
            visitor_team = linescores[linescores['TEAM_ID'] == visitor_team_id]

            home_name = (home_team.iloc[0]['TEAM_CITY_NAME'] + " " + home_team.iloc[0]['TEAM_NAME']) if not home_team.empty else "Unknown Home"
            visitor_name = (visitor_team.iloc[0]['TEAM_CITY_NAME'] + " " + visitor_team.iloc[0]['TEAM_NAME']) if not visitor_team.empty else "Unknown Visitor"

            print(f" - {visitor_name} vs {home_name} [{game_status}]")

except Exception as e:
    print("❌ Failed to fetch games:", e)