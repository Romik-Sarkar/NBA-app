from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import json
import os
import traceback  # Added explicit import
from nba_api.stats.endpoints import leaguegamefinder, teamgamelog, commonteamroster, teaminfocommon, scoreboardv2, leaguestandings, teamdashboardbygeneralsplits, playergamelog
from nba_api.stats.static import teams, players
from nba_api.stats.library.parameters import SeasonType
import pandas as pd
import numpy as np
import time  # To handle rate limiting


app = Flask(__name__, static_folder='static', template_folder='templates')


# Get all NBA teams for reference
try:
    NBA_TEAMS = teams.get_teams()
    TEAM_ID_MAP = {team['abbreviation']: team['id'] for team in NBA_TEAMS}
    TEAM_NAME_MAP = {team['abbreviation']: team['full_name'] for team in NBA_TEAMS}
except Exception as e:
    print(f"Error loading NBA teams: {str(e)}")
    NBA_TEAMS = []
    TEAM_ID_MAP = {}
    TEAM_NAME_MAP = {}

@app.route('/')
def index():
    """Render the main page."""
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', current_date=today)

@app.route('/api/teams')
def get_nba_teams():
    nba_teams = teams.get_teams()
    
    # You can customize what fields to return
    team_list = [
        {
            "id": team["id"],
            "full_name": team["full_name"],
            "abbreviation": team["abbreviation"],
            "city": team["city"],
        }
        for team in nba_teams
    ]
    
    return jsonify(team_list)

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get NBA games for a specific date."""
    try:
        # Get date from query parameters, default to today
        game_date = request.args.get('date', datetime.now().strftime('%m/%d/%Y'))
        
        # Fetch scoreboard data
        scoreboard = scoreboardv2.ScoreboardV2(game_date=game_date)
        
        game_headers = scoreboard.get_data_frames()[0]  # GameHeader
        linescores = scoreboard.get_data_frames()[1]    # LineScore
        
        games_data = []
        
        if not game_headers.empty:
            for _, game in game_headers.iterrows():
                home_team_id = game['HOME_TEAM_ID']
                visitor_team_id = game['VISITOR_TEAM_ID']
                game_status = game['GAME_STATUS_TEXT']
                game_status_id = game['GAME_STATUS_ID']
                game_id = game['GAME_ID']
                
                # Get team names from LineScore
                home_team = linescores[linescores['TEAM_ID'] == home_team_id]
                visitor_team = linescores[linescores['TEAM_ID'] == visitor_team_id]
                
                home_name = home_team.iloc[0]['TEAM_CITY_NAME'] + " " + home_team.iloc[0]['TEAM_NAME'] if not home_team.empty else "Unknown Home"
                visitor_name = visitor_team.iloc[0]['TEAM_CITY_NAME'] + " " + visitor_team.iloc[0]['TEAM_NAME'] if not visitor_team.empty else "Unknown Visitor"
                
                # Get team scores if available
                home_score = int(home_team.iloc[0]['PTS']) if not home_team.empty and 'PTS' in home_team.columns and pd.notna(home_team.iloc[0]['PTS']) else None
                visitor_score = int(visitor_team.iloc[0]['PTS']) if not visitor_team.empty and 'PTS' in visitor_team.columns and pd.notna(visitor_team.iloc[0]['PTS']) else None
                
                # Game time info
                game_time = game.get('GAME_STATUS_TEXT', '')
                
                # Team abbreviations
                home_abbr = home_team.iloc[0]['TEAM_ABBREVIATION'] if not home_team.empty else ""
                visitor_abbr = visitor_team.iloc[0]['TEAM_ABBREVIATION'] if not visitor_team.empty else ""
                
                games_data.append({
                    'game_id': game_id,
                    'home_team': {
                        'id': int(home_team_id),
                        'name': home_name,
                        'abbreviation': home_abbr,
                        'score': home_score
                    },
                    'visitor_team': {
                        'id': int(visitor_team_id),
                        'name': visitor_name,
                        'abbreviation': visitor_abbr,
                        'score': visitor_score
                    },
                    'status': {
                        'id': int(game_status_id),
                        'text': game_status
                    },
                    'game_time': game_time
                })
        
        return jsonify({
            'games': games_data,
            'date': game_date
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'games': []
        }), 500

@app.route('/api/standings')
def get_standings():
    """Get current NBA standings"""
    try:
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

        
        return jsonify(merged_df.to_dict(orient='records'))
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in standings API: {str(e)}\n{error_details}")
        
        return jsonify({
            'error': True,
            'message': f'Failed to load standings data: {str(e)}'
        }), 500
    
@app.route('/teams')
def teams_page():
    """Render the teams page."""
    return render_template('teams.html')

def convert_min_to_float(min_str):
    """Convert minutes string (e.g. '12:30') to float (12.5)"""
    # If min_str is a string with ':', convert MM:SS to float minutes
    if isinstance(min_str, str) and ':' in min_str:
        minutes, seconds = min_str.split(':')
        return int(minutes) + int(seconds) / 60
    try:
        # Otherwise, convert directly to float (for integer minute strings or ints)
        return float(min_str)
    except (ValueError, TypeError):
        return 0.0

def get_player_season_averages(player_id, team_id=None, season='2024-25'):
    """Get player season averages with enhanced statistics"""
    try:
        # Get all player game logs for the season
        logs = playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star=SeasonType.regular
        ).get_data_frames()[0]
        
        if logs.empty:
            return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
        
        # If team_id is provided, filter logs to only include games for that team
        if team_id is not None:
            # Get the team abbreviation for our team_id
            nba_teams = teams.get_teams()
            team_abbr = next((team['abbreviation'] for team in nba_teams if team['id'] == team_id), None)
            
            if team_abbr is not None:
                # Filter logs to only include games where player was on this team
                # MATCHUP format is either "TEAM vs. OPP" or "TEAM @ OPP" where TEAM is player's team
                logs = logs[logs['MATCHUP'].str.startswith(team_abbr)]
        
        if logs.empty:
            return {k: 0 for k in ['GP','MIN','PTS','OREB','DREB','REB','AST','STL','BLK','TO','PF','AST_TO']}
        
        gp = logs.shape[0]
        logs.loc[:, 'MIN_float'] = logs['MIN'].apply(convert_min_to_float)
        avg_min = logs['MIN_float'].mean()
        avg_pts = logs['PTS'].mean()
        avg_oreb = logs['OREB'].mean()
        avg_dreb = logs['DREB'].mean()
        avg_reb = logs['REB'].mean()
        avg_ast = logs['AST'].mean()
        avg_stl = logs['STL'].mean()
        avg_blk = logs['BLK'].mean()
        avg_to = logs['TOV'].mean() if 'TOV' in logs.columns else 0
        avg_pf = logs['PF'].mean()
        
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

@app.route('/team/<int:team_id>')
def team_page(team_id):
    """Render the team page with detailed information."""
    try:
        print(f"Debug: Accessing team page for team_id: {team_id}")
        
        # Get team info using NBA API
        team_info_common = teaminfocommon.TeamInfoCommon(team_id=team_id)
        team_info_df = team_info_common.get_data_frames()[0]
        
        if team_info_df.empty:
            print(f"Debug: No team info found for team_id: {team_id}")
            return render_template('404.html', message=f"Team with ID {team_id} not found"), 404
        
        print(f"Debug: Team info found: {team_info_df.iloc[0]['TEAM_NAME']}")
        
        # Build a simple team object first to ensure we have basic data
        team_data = {
            'id': team_id,
            'full_name': team_info_df.iloc[0]['TEAM_NAME'],
            'abbreviation': team_info_df.iloc[0]['TEAM_ABBREVIATION'],
            'conference': team_info_df.iloc[0]['TEAM_CONFERENCE']
        }
        
        # Create a basic team stats object
        team_stats = {
            'wins': team_info_df.iloc[0]['W'],
            'losses': team_info_df.iloc[0]['L'],
            'win_pct': float(team_info_df.iloc[0]['PCT']),
            'points_per_game': 0.0,
            'rebounds_per_game': 0.0,
            'assists_per_game': 0.0
        }
        
        # Try to get roster data
        try:
            print(f"Debug: Fetching roster for team_id: {team_id}")
            roster_endpoint = commonteamroster.CommonTeamRoster(team_id=team_id)
            roster_df = roster_endpoint.get_data_frames()[0]
            
            # Process roster data with player stats
            roster = []
            for _, player in roster_df.iterrows():
                player_id = player['PLAYER_ID']
                
                # Get player stats
                try:
                    stats = get_player_season_averages(player_id, team_id)
                    
                    roster.append({
                        'name': player['PLAYER'],
                        'position': player['POSITION'],
                        'jersey': player['NUM'],
                        'height': player['HEIGHT'],
                        'weight': player['WEIGHT'],
                        'age': player.get('AGE', 'N/A'),
                        'gp': stats['GP'],
                        'min': stats['MIN'],
                        'ppg': stats['PTS'],
                        'oreb': stats['OREB'],
                        'dreb': stats['DREB'],
                        'rpg': stats['REB'],
                        'apg': stats['AST'],
                        'spg': stats['STL'],
                        'bpg': stats['BLK'],
                        'to': stats['TO'],
                        'pf': stats['PF'],
                        'ast_to': stats['AST_TO']
                    })
                    
                    # Add a small delay to avoid rate limiting
                    time.sleep(0.6)
                    
                except Exception as player_err:
                    print(f"Error getting stats for player {player['PLAYER']}: {str(player_err)}")
                    roster.append({
                        'name': player['PLAYER'],
                        'position': player['POSITION'],
                        'jersey': player['NUM'],
                        'height': player['HEIGHT'],
                        'weight': player['WEIGHT'],
                        'age': player.get('AGE', 'N/A'),
                        'gp': 0,
                        'min': 0.0,
                        'ppg': 0.0,
                        'oreb': 0.0,
                        'dreb': 0.0,
                        'rpg': 0.0,
                        'apg': 0.0,
                        'spg': 0.0,
                        'bpg': 0.0,
                        'to': 0.0,
                        'pf': 0.0,
                        'ast_to': 0.0
                    })
            
            print(f"Debug: Found {len(roster)} players in roster")
        except Exception as e:
            print(f"Debug: Error fetching roster: {str(e)}")
            roster = []
        
        # Try to get advanced stats
        try:
            print(f"Debug: Fetching team stats for team_id: {team_id}")
            team_stats_endpoint = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
                team_id=team_id,
                season="2024-25",
                per_mode_detailed="PerGame"
            )
            
            team_stats_df = team_stats_endpoint.get_data_frames()[0]
            
            if not team_stats_df.empty:
                stats_row = team_stats_df.iloc[0]
                team_stats['points_per_game'] = float(stats_row.get('PTS', 0))
                team_stats['rebounds_per_game'] = float(stats_row.get('REB', 0))
                team_stats['assists_per_game'] = float(stats_row.get('AST', 0))
            print(f"Debug: Team stats: PPG={team_stats['points_per_game']}")
        except Exception as e:
            print(f"Debug: Error fetching team stats: {str(e)}")
            # Keep default stats
        
        # Mock upcoming games for now
        upcoming_games = [
            {
                'date': (datetime.now() + timedelta(days=i)).strftime('%b %d, %Y'),
                'opponent': f"Team {i+1}",
                'is_home': i % 2 == 0,
                'win_probability': round(50 + (i * 5))
            }
            for i in range(5)
        ]
        
        print(f"Debug: Rendering team template with data")
        return render_template(
            'team.html',
            team=team_data,
            team_stats=team_stats,
            roster=roster,
            upcoming_games=upcoming_games
        )
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error rendering team page: {str(e)}\n{error_details}")
        
        # Instead of redirecting to index, show an error page with details
        return render_template('500.html', 
                              message=f"Error loading team page: {str(e)}",
                              details=error_details), 500

# Add API endpoints for team data to support client-side rendering if needed
@app.route('/api/team/<int:team_id>/roster')
def team_roster_api(team_id):
    """API endpoint to get team roster"""
    try:
        roster_endpoint = commonteamroster.CommonTeamRoster(team_id=team_id)
        roster_df = roster_endpoint.get_data_frames()[0]
        return jsonify(roster_df.to_dict('records'))
    except Exception as e:
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500

@app.route('/api/team/<int:team_id>/games')
def team_games_api(team_id):
    """API endpoint to get team games"""
    try:
        # Number of games to return, default to 10
        count = int(request.args.get('count', 10))
        
        games_endpoint = teamgamelog.TeamGameLog(team_id=team_id, season="2024-25")
        games_df = games_endpoint.get_data_frames()[0].head(count)
        return jsonify(games_df.to_dict('records'))
    except Exception as e:
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500

@app.route('/api/team/<int:team_id>/player-stats')
def player_stats_api(team_id):
    """API endpoint to get player stats for a team"""
    try:
        # Get team roster
        roster_endpoint = commonteamroster.CommonTeamRoster(team_id=team_id)
        roster_df = roster_endpoint.get_data_frames()[0]
        
        player_stats = []
        
        # Get stats for each player
        for _, player in roster_df.iterrows():
            player_id = player['PLAYER_ID']
            player_name = player['PLAYER']
            
            # Get player stats
            try:
                stats = get_player_season_averages(player_id, team_id)
                
                player_stats.append({
                    'PLAYER': player_name,
                    'PLAYER_ID': player_id,
                    'NUM': player['NUM'],
                    'POSITION': player['POSITION'],
                    'HEIGHT': player['HEIGHT'],
                    'WEIGHT': player['WEIGHT'],
                    'GP': stats['GP'],
                    'MIN': stats['MIN'],
                    'PTS': stats['PTS'],
                    'OREB': stats['OREB'],
                    'DREB': stats['DREB'], 
                    'REB': stats['REB'],
                    'AST': stats['AST'],
                    'STL': stats['STL'],
                    'BLK': stats['BLK'],
                    'TO': stats['TO'],
                    'PF': stats['PF'],
                    'AST_TO': stats['AST_TO']
                })
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.6)
                
            except Exception as e:
                print(f"Error getting stats for player {player_name}: {str(e)}")
                
                # Add player with zero stats
                player_stats.append({
                    'PLAYER': player_name,
                    'PLAYER_ID': player_id,
                    'NUM': player['NUM'],
                    'POSITION': player['POSITION'],
                    'HEIGHT': player['HEIGHT'],
                    'WEIGHT': player['WEIGHT'],
                    'GP': 0,
                    'MIN': 0,
                    'PTS': 0.0,
                    'OREB': 0.0,
                    'DREB': 0.0,
                    'REB': 0.0,
                    'AST': 0.0,
                    'STL': 0.0,
                    'BLK': 0.0,
                    'TO': 0.0,
                    'PF': 0.0,
                    'AST_TO': 0.0
                })
        
        return jsonify(player_stats)
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in player stats API: {str(e)}\n{error_details}")
        
        return jsonify({
            'error': True,
            'message': f'Failed to load player stats: {str(e)}'
        }), 500

@app.route('/analytics')
def analytics():
    """Render the analytics page."""
    return render_template('analytics.html')

@app.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html')

@app.route('/how-it-works')
def how_it_works():
    """Render the how it works page."""
    return render_template('howItWorks.html')

@app.route('/algorithm')
def algorithm():
    """Render the algorithm page."""
    return render_template('algorithm.html')

@app.route('/historical-accuracy')
def historical_accuracy():
    """Render the historical accuracy page."""
    return render_template('historicalAccuracy.html')

@app.template_filter('date_format')
def date_format_filter(date_str):
    """Format date strings for display"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%b %d, %Y')
    except:
        return date_str

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)