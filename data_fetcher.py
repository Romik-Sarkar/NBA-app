# data_fetcher.py - Enhanced data fetcher to populate database with NBA API data
from nba_api.stats.static import teams
from nba_api.stats.endpoints import (
    leaguestandings, 
    commonteamroster, 
    playergamelog,
    teamgamelog,
    scoreboardv2,
    teamdashboardbygeneralsplits
)
from nba_api.stats.library.parameters import SeasonType
from datetime import datetime, timedelta
import pandas as pd
import time
import traceback
from db import db, Team, TeamStats, Player, PlayerStats, Game, RefreshTracker, should_refresh, update_refresh_time

def safe_api_call(api_func, *args, **kwargs):
    """Safely make API calls with retry logic and rate limiting"""
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            time.sleep(0.6)  # Rate limiting
            result = api_func(*args, **kwargs)
            return result
        except Exception as e:
            print(f"API call attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
            else:
                raise e

def convert_min_to_float(min_str):
    """Convert MM:SS format to float minutes"""
    if isinstance(min_str, str) and ':' in min_str:
        try:
            minutes, seconds = min_str.split(':')
            return int(minutes) + int(seconds) / 60
        except ValueError:
            return 0.0
    try:
        return float(min_str)
    except (ValueError, TypeError):
        return 0.0

def fetch_and_store_teams():
    """Fetch all NBA teams and store in database"""
    try:
        if not should_refresh('teams', hours=24):  # Refresh teams daily
            print("Teams data is fresh, skipping refresh")
            return True
            
        print("Fetching NBA teams...")
        nba_teams = teams.get_teams()
        
        for team_data in nba_teams:
            team = Team.query.get(team_data['id'])
            if team:
                # Update existing team
                team.abbreviation = team_data['abbreviation']
                team.full_name = team_data['full_name']
                team.city = team_data['city']
                team.name = team_data['nickname']
                team.last_updated = datetime.utcnow()
            else:
                # Create new team - conference will be set by update_team_conferences()
                conference_mapping = get_team_conference_mapping()
                team = Team(
                    id=team_data['id'],
                    abbreviation=team_data['abbreviation'],
                    full_name=team_data['full_name'],
                    city=team_data['city'],
                    name=team_data['nickname'],
                    conference=conference_mapping.get(team_data['id'], 'Unknown')
                )
                db.session.add(team)
        
        db.session.commit()
        update_refresh_time('teams')
        print(f"Successfully stored {len(nba_teams)} teams")
        return True
        
    except Exception as e:
        print(f"Error fetching teams: {str(e)}")
        db.session.rollback()
        return False

def fetch_and_store_standings():
    """Fetch current NBA standings and store team stats"""
    try:
        if not should_refresh('standings', hours=6):
            print("Standings data is fresh, skipping refresh")
            return True
            
        print("Fetching NBA standings...")
        standings_api = safe_api_call(leaguestandings.LeagueStandings)
        standings_df = standings_api.get_data_frames()[0]
        
        for _, row in standings_df.iterrows():
            team_id = row['TeamID']
            
            # Ensure team exists
            team = Team.query.get(team_id)
            if not team:
                continue
                
            # Update team conference if not set
            if not team.conference:
                team.conference = row['Conference']
            
            # Update or create team stats
            team_stats = TeamStats.query.get(team_id)
            if team_stats:
                team_stats.wins = row['WINS']
                team_stats.losses = row['LOSSES']
                team_stats.win_pct = row['WinPCT']
                team_stats.conference_rank = row['PlayoffRank']
                team_stats.last_updated = datetime.utcnow()
            else:
                team_stats = TeamStats(
                    team_id=team_id,
                    wins=row['WINS'],
                    losses=row['LOSSES'],
                    win_pct=row['WinPCT'],
                    conference_rank=row['PlayoffRank']
                )
                db.session.add(team_stats)
        
        db.session.commit()
        update_refresh_time('standings')
        print("Successfully updated standings")
        return True
        
    except Exception as e:
        print(f"Error fetching standings: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return False

def fetch_and_store_team_stats(team_id, season='2024-25'):
    """Fetch detailed team stats and update database"""
    try:
        print(f"Fetching team stats for team ID: {team_id}")
        
        # Get team dashboard stats
        team_dashboard = safe_api_call(
            teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits,
            team_id=team_id,
            season=season
        )
        
        # Get overall team stats (first row contains season averages)
        team_stats_df = team_dashboard.get_data_frames()[0]
        
        if not team_stats_df.empty:
            stats_row = team_stats_df.iloc[0]
            
            team_stats = TeamStats.query.get(team_id)
            if team_stats:
                team_stats.points_per_game = stats_row.get('PTS', 0.0)
                team_stats.rebounds_per_game = stats_row.get('REB', 0.0)
                team_stats.assists_per_game = stats_row.get('AST', 0.0)
                team_stats.last_updated = datetime.utcnow()
            else:
                team_stats = TeamStats(
                    team_id=team_id,
                    points_per_game=stats_row.get('PTS', 0.0),
                    rebounds_per_game=stats_row.get('REB', 0.0),
                    assists_per_game=stats_row.get('AST', 0.0)
                )
                db.session.add(team_stats)
        
        db.session.commit()
        print(f"Successfully updated team stats for team {team_id}")
        return True
        
    except Exception as e:
        print(f"Error fetching team stats for team {team_id}: {str(e)}")
        db.session.rollback()
        return False

def fetch_and_store_team_roster(team_id, season='2024-25'):
    """Fetch team roster and player stats"""
    try:
        print(f"Fetching roster for team ID: {team_id}")
        
        # Get team roster
        roster_api = safe_api_call(commonteamroster.CommonTeamRoster, team_id=team_id, season=season)
        roster_df = roster_api.get_data_frames()[0]
        
        # Get team info for filtering player stats
        team = Team.query.get(team_id)
        if not team:
            print(f"Team {team_id} not found in database")
            return False
        
        for _, player_row in roster_df.iterrows():
            player_id = player_row['PLAYER_ID']
            
            # Update or create player
            player = Player.query.get(player_id)
            if player:
                player.full_name = player_row['PLAYER']
                player.jersey = str(player_row['NUM']) if pd.notna(player_row['NUM']) else None
                player.position = player_row['POSITION']
                player.height = player_row['HEIGHT']
                player.weight = str(player_row['WEIGHT']) if pd.notna(player_row['WEIGHT']) else None
                player.team_id = team_id
                player.last_updated = datetime.utcnow()
            else:
                player = Player(
                    id=player_id,
                    full_name=player_row['PLAYER'],
                    jersey=str(player_row['NUM']) if pd.notna(player_row['NUM']) else None,
                    position=player_row['POSITION'],
                    height=player_row['HEIGHT'],
                    weight=str(player_row['WEIGHT']) if pd.notna(player_row['WEIGHT']) else None,
                    team_id=team_id
                )
                db.session.add(player)
            
            # Get player season stats using the corrected function
            player_stats = get_player_season_stats(player_id, team_id, season)
            
            # Update or create player stats
            existing_stats = PlayerStats.query.get(player_id)
            if existing_stats:
                existing_stats.gp = player_stats['GP']
                existing_stats.min_pg = player_stats['MIN']
                existing_stats.pts_pg = player_stats['PTS']
                existing_stats.oreb_pg = player_stats['OREB']
                existing_stats.dreb_pg = player_stats['DREB']
                existing_stats.reb_pg = player_stats['REB']
                existing_stats.ast_pg = player_stats['AST']
                existing_stats.stl_pg = player_stats['STL']
                existing_stats.blk_pg = player_stats['BLK']
                existing_stats.to_pg = player_stats['TO']
                existing_stats.pf_pg = player_stats['PF']
                existing_stats.ast_to = player_stats['AST_TO']
                existing_stats.last_updated = datetime.utcnow()
            else:
                stats_record = PlayerStats(
                    player_id=player_id,
                    gp=player_stats['GP'],
                    min_pg=player_stats['MIN'],
                    pts_pg=player_stats['PTS'],
                    oreb_pg=player_stats['OREB'],
                    dreb_pg=player_stats['DREB'],
                    reb_pg=player_stats['REB'],
                    ast_pg=player_stats['AST'],
                    stl_pg=player_stats['STL'],
                    blk_pg=player_stats['BLK'],
                    to_pg=player_stats['TO'],
                    pf_pg=player_stats['PF'],
                    ast_to=player_stats['AST_TO']
                )
                db.session.add(stats_record)
        
        db.session.commit()
        print(f"Successfully updated roster for team {team_id}")
        return True
        
    except Exception as e:
        print(f"Error fetching roster for team {team_id}: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return False

def get_player_season_stats(player_id, team_id, season='2024-25'):
    """Get player season averages - FIXED VERSION following test.py pattern"""
    try:
        # Get player game logs
        logs_api = safe_api_call(
            playergamelog.PlayerGameLog,
            player_id=player_id,
            season=season,
            season_type_all_star=SeasonType.regular
        )
        logs_df = logs_api.get_data_frames()[0]
        
        if logs_df.empty:
            return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
        
        # Get team abbreviation for filtering - FIXED: Use team_id instead of team_abbr parameter
        nba_teams = teams.get_teams()
        team_abbr = next((team['abbreviation'] for team in nba_teams if team['id'] == team_id), None)
        
        if team_abbr is None:
            return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
        
        # Filter logs for current team - FIXED: Use the exact same logic as test.py
        team_logs = logs_df[logs_df['MATCHUP'].str.startswith(team_abbr)].copy()
        
        if team_logs.empty:
            return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
        
        # Calculate averages - FIXED: Use the exact same logic as test.py
        gp = team_logs.shape[0]  # Use shape[0] like in test.py
        team_logs.loc[:, 'MIN_float'] = team_logs['MIN'].apply(convert_min_to_float)
        
        avg_min = team_logs['MIN_float'].mean()
        avg_pts = team_logs['PTS'].mean()
        avg_oreb = team_logs['OREB'].mean()
        avg_dreb = team_logs['DREB'].mean()
        avg_reb = team_logs['REB'].mean()
        avg_ast = team_logs['AST'].mean()
        avg_stl = team_logs['STL'].mean()
        avg_blk = team_logs['BLK'].mean()
        avg_to = team_logs['TOV'].mean()  # Note: TOV in API response
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
        print(f"Error getting stats for player {player_id}: {str(e)}")
        return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}

def fetch_and_store_games(date_str=None):
    """Fetch games for a specific date"""
    try:
        if date_str is None:
            date_str = datetime.now().strftime('%m/%d/%Y')
            
        print(f"Fetching games for {date_str}")
        
        # Convert date format for API call
        try:
            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
        api_date_str = date_obj.strftime('%m/%d/%Y')
        db_date = date_obj.date()
        
        # Get scoreboard for the date
        scoreboard = safe_api_call(scoreboardv2.ScoreboardV2, game_date=api_date_str)
        games_df = scoreboard.get_data_frames()[0]  # GameHeader
        line_score_df = scoreboard.get_data_frames()[1]  # LineScore
        
        for _, game_row in games_df.iterrows():
            game_id = game_row['GAME_ID']
            
            # Get scores from line score data
            game_line_scores = line_score_df[line_score_df['GAME_ID'] == game_id]
            home_score = None
            visitor_score = None
            
            if not game_line_scores.empty:
                home_team_row = game_line_scores[game_line_scores['TEAM_ID'] == game_row['HOME_TEAM_ID']]
                visitor_team_row = game_line_scores[game_line_scores['TEAM_ID'] == game_row['VISITOR_TEAM_ID']]
                
                if not home_team_row.empty:
                    home_score = home_team_row['PTS'].iloc[0]
                if not visitor_team_row.empty:
                    visitor_score = visitor_team_row['PTS'].iloc[0]
            
            # Update or create game
            game = Game.query.get(game_id)
            if game:
                game.home_team_score = home_score
                game.visitor_team_score = visitor_score
                game.status_id = game_row['GAME_STATUS_ID']
                game.status_text = game_row['GAME_STATUS_TEXT']
                game.last_updated = datetime.utcnow()
            else:
                game = Game(
                    id=game_id,
                    home_team_id=game_row['HOME_TEAM_ID'],
                    visitor_team_id=game_row['VISITOR_TEAM_ID'],
                    game_date=db_date,
                    game_time=game_row.get('GAME_STATUS_TEXT', ''),
                    status_id=game_row['GAME_STATUS_ID'],
                    status_text=game_row['GAME_STATUS_TEXT'],
                    home_team_score=home_score,
                    visitor_team_score=visitor_score
                )
                db.session.add(game)
        
        db.session.commit()
        print(f"Successfully updated games for {date_str}")
        return True
        
    except Exception as e:
        print(f"Error fetching games: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return False

def initialize_database():
    """Initialize database with essential data"""
    try:
        print("Initializing database with NBA data...")
        
        # Fetch teams first (required for other data)
        if fetch_and_store_teams():
            print("✓ Teams loaded")
        else:
            print("✗ Failed to load teams")
            return False
        
        # Fetch standings (includes basic team stats)
        if fetch_and_store_standings():
            print("✓ Standings loaded")
        else:
            print("✗ Failed to load standings")
        
        # Fetch today's games
        if fetch_and_store_games():
            print("✓ Today's games loaded")
        else:
            print("✗ Failed to load today's games")
        
        print("Database initialization completed!")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        return False

def refresh_all_team_data():
    """Refresh roster and stats for all teams"""
    try:
        teams_list = Team.query.all()
        print(f"Refreshing data for {len(teams_list)} teams...")
        
        for i, team in enumerate(teams_list, 1):
            print(f"Processing team {i}/{len(teams_list)}: {team.full_name}")
            
            # Fetch team stats
            fetch_and_store_team_stats(team.id)
            
            # Fetch roster (this is time-consuming due to player stats)
            fetch_and_store_team_roster(team.id)
            
            # Add delay to avoid rate limiting
            time.sleep(2)
        
        print("All team data refreshed!")
        return True
        
    except Exception as e:
        print(f"Error refreshing team data: {str(e)}")
        return False

# Utility functions for maintenance
def get_team_conference_mapping():
    """Return proper conference mapping for teams"""
    eastern_teams = {
        1610612737: 'East',  # Atlanta Hawks
        1610612738: 'East',  # Boston Celtics
        1610612751: 'East',  # Brooklyn Nets
        1610612766: 'East',  # Charlotte Hornets
        1610612741: 'East',  # Chicago Bulls
        1610612739: 'East',  # Cleveland Cavaliers
        1610612743: 'West',  # Denver Nuggets
        1610612765: 'East',  # Detroit Pistons
        1610612744: 'West',  # Golden State Warriors
        1610612745: 'West',  # Houston Rockets
        1610612754: 'East',  # Indiana Pacers
        1610612746: 'West',  # LA Clippers
        1610612747: 'West',  # Los Angeles Lakers
        1610612763: 'West',  # Memphis Grizzlies
        1610612748: 'East',  # Miami Heat
        1610612749: 'East',  # Milwaukee Bucks
        1610612750: 'West',  # Minnesota Timberwolves
        1610612740: 'West',  # New Orleans Pelicans
        1610612752: 'East',  # New York Knicks
        1610612760: 'West',  # Oklahoma City Thunder
        1610612753: 'East',  # Orlando Magic
        1610612755: 'East',  # Philadelphia 76ers
        1610612756: 'West',  # Phoenix Suns
        1610612757: 'West',  # Portland Trail Blazers
        1610612758: 'West',  # Sacramento Kings
        1610612759: 'West',  # San Antonio Spurs
        1610612761: 'East',  # Toronto Raptors
        1610612762: 'West',  # Utah Jazz
        1610612764: 'East',  # Washington Wizards
        1610612742: 'West',  # Dallas Mavericks
    }
    return eastern_teams

def update_team_conferences():
    """Update team conferences in database"""
    try:
        conference_mapping = get_team_conference_mapping()
        
        for team_id, conference in conference_mapping.items():
            team = Team.query.get(team_id)
            if team:
                team.conference = conference
                
        db.session.commit()
        print("Team conferences updated successfully")
        return True
        
    except Exception as e:
        print(f"Error updating team conferences: {str(e)}")
        db.session.rollback()
        return False

# FIXED: Updated helper functions to use team_id instead of team_abbr
def update_player_stats_only(player_id, team_id=None, season='2024-25'):
    """Update stats for a single player without touching roster info"""
    try:
        # Get player info
        player = Player.query.get(player_id)
        if not player:
            print(f"Player {player_id} not found in database")
            return False
        
        # Use player's team_id if not provided
        if not team_id:
            team_id = player.team_id
        
        # Get team info
        team = Team.query.get(team_id)
        if not team:
            print(f"Team {team_id} not found")
            return False
        
        print(f"Updating stats for {player.full_name} ({team.abbreviation})...")
        
        # Get updated stats using the corrected function
        player_stats = get_player_season_stats(player_id, team_id, season)
        
        # Update or create player stats
        existing_stats = PlayerStats.query.get(player_id)
        if existing_stats:
            existing_stats.gp = player_stats['GP']
            existing_stats.min_pg = player_stats['MIN']
            existing_stats.pts_pg = player_stats['PTS']
            existing_stats.oreb_pg = player_stats['OREB']
            existing_stats.dreb_pg = player_stats['DREB']
            existing_stats.reb_pg = player_stats['REB']
            existing_stats.ast_pg = player_stats['AST']
            existing_stats.stl_pg = player_stats['STL']
            existing_stats.blk_pg = player_stats['BLK']
            existing_stats.to_pg = player_stats['TO']
            existing_stats.pf_pg = player_stats['PF']
            existing_stats.ast_to = player_stats['AST_TO']
            existing_stats.last_updated = datetime.utcnow()
        else:
            stats_record = PlayerStats(
                player_id=player_id,
                gp=player_stats['GP'],
                min_pg=player_stats['MIN'],
                pts_pg=player_stats['PTS'],
                oreb_pg=player_stats['OREB'],
                dreb_pg=player_stats['DREB'],
                reb_pg=player_stats['REB'],
                ast_pg=player_stats['AST'],
                stl_pg=player_stats['STL'],
                blk_pg=player_stats['BLK'],
                to_pg=player_stats['TO'],
                pf_pg=player_stats['PF'],
                ast_to=player_stats['AST_TO']
            )
            db.session.add(stats_record)
        
        db.session.commit()
        print(f"✓ Updated stats for {player.full_name}: {player_stats['PTS']} PPG, {player_stats['REB']} RPG, {player_stats['AST']} APG")
        return True
        
    except Exception as e:
        print(f"❌ Error updating stats for player {player_id}: {str(e)}")
        db.session.rollback()
        return False

def update_team_player_stats_only(team_id, season='2024-25'):
    """Update stats for all players on a specific team (stats only, no roster changes)"""
    try:
        # Get team info
        team = Team.query.get(team_id)
        if not team:
            print(f"Team {team_id} not found")
            return False
        
        # Get all players for this team
        players = Player.query.filter_by(team_id=team_id).all()
        if not players:
            print(f"No players found for {team.full_name}")
            return False
        
        print(f"Updating stats for {len(players)} players on {team.full_name}...")
        
        success_count = 0
        for i, player in enumerate(players, 1):
            print(f"Progress: {i}/{len(players)} - {player.full_name}")
            
            if update_player_stats_only(player.id, team_id, season):
                success_count += 1
            
            # Rate limiting
            time.sleep(0.6)
        
        print(f"✓ Successfully updated stats for {success_count}/{len(players)} players on {team.full_name}")
        return success_count == len(players)
        
    except Exception as e:
        print(f"❌ Error updating team player stats: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the data fetcher
    print("Testing NBA Data Fetcher...")
    
    # Initialize database
    from db import app
    with app.app_context():
        db.create_all()
        
        # Test basic functions
        print("\n1. Testing teams fetch...")
        fetch_and_store_teams()
        
        print("\n2. Updating team conferences...")
        update_team_conferences()
        
        print("\n3. Testing standings fetch...")
        fetch_and_store_standings()
        
        print("\n4. Testing games fetch...")
        fetch_and_store_games()
        
        print("\n5. Testing Lakers roster fetch...")
        lakers_id = 1610612747  # Lakers team ID
        fetch_and_store_team_roster(lakers_id)
        
        print("\nData fetcher test completed!")