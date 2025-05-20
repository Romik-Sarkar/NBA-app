from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import json
import os
from nba_api.stats.endpoints import leaguegamefinder, teamgamelog, commonteamroster, teaminfocommon, scoreboardv2
from nba_api.stats.static import teams
import pandas as pd
import numpy as np


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

@app.route('/teams')
def teams_page():
    """Render the teams page."""
    return render_template('teams.html')

@app.route('/team/<int:team_id>')
def team_page(team_id):
    """Render the team page."""
    try:
        # Get team info using NBA API
        team_info = teaminfocommon.TeamInfoCommon(team_id=team_id)
        team_info_df = team_info.get_data_frames()[0]
        
        if team_info_df.empty:
            return redirect(url_for('index'))
        
        # Find the team in our NBA_TEAMS list
        team_data = next((team for team in NBA_TEAMS if team['id'] == team_id), None)
        
        if not team_data:
            return redirect(url_for('index'))
        
        return render_template('team.html', team_id=team_id)
    except Exception as e:
        print(f"Error rendering team page: {str(e)}")
        return redirect(url_for('index'))


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