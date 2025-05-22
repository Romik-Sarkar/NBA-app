from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import json
import os
import traceback
import time
from sqlalchemy import func
from db import app, db, Team, TeamStats, Player, PlayerStats, Game, RefreshTracker
from data_fetcher import (
    fetch_and_store_teams, 
    fetch_and_store_standings, 
    fetch_and_store_team_stats,
    fetch_and_store_team_roster,
    fetch_and_store_games,
    initialize_database
)

# Initialize database on startup
with app.app_context():
    db.create_all()
    try:
        # Initialize with basic data if database is empty
        if Team.query.count() == 0:
            initialize_database()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")

@app.route('/')
def index():
    """Render the main page with games data from database."""
    try:
        # Get date from query parameters, default to today
        game_date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Convert to proper date format for database query
        try:
            game_date_obj = datetime.strptime(game_date_str, '%Y-%m-%d').date()
        except ValueError:
            # Try other format
            try:
                game_date_obj = datetime.strptime(game_date_str, '%m/%d/%Y').date()
                game_date_str = game_date_obj.strftime('%Y-%m-%d')
            except ValueError:
                game_date_obj = datetime.now().date()
                game_date_str = game_date_obj.strftime('%Y-%m-%d')
        
        # Get all teams for the filter dropdown
        teams = Team.query.order_by(Team.full_name).all()
        
        # Query games from database
        games_query = db.session.query(Game).filter(Game.game_date == game_date_obj).all()
        
        games_data = []
        for game in games_query:
            # Get team info
            home_team = Team.query.get(game.home_team_id)
            visitor_team = Team.query.get(game.visitor_team_id)
            
            if not home_team or not visitor_team:
                continue
            
            games_data.append({
                'game_id': game.id,
                'home_team': {
                    'id': home_team.id,
                    'name': home_team.full_name,
                    'abbreviation': home_team.abbreviation,
                    'score': game.home_team_score
                },
                'visitor_team': {
                    'id': visitor_team.id,
                    'name': visitor_team.full_name,
                    'abbreviation': visitor_team.abbreviation,
                    'score': game.visitor_team_score
                },
                'status': {
                    'id': game.status_id,
                    'text': game.status_text
                },
                'game_time': game.game_time,
                'home_win_probability': 50,  # Default values - you can implement actual ML predictions
                'visitor_win_probability': 50
            })
        
        return render_template('index.html', 
                             current_date=game_date_str,
                             games=games_data,
                             teams=teams)
                             
    except Exception as e:
        print(f"Error rendering index page: {str(e)}")
        traceback.print_exc()
        return render_template('index.html', 
                             current_date=datetime.now().strftime('%Y-%m-%d'),
                             games=[],
                             teams=[])

@app.route('/api/teams')
def get_nba_teams():
    """Get all NBA teams from database."""
    try:
        teams = Team.query.all()
        team_list = [
            {
                "id": team.id,
                "full_name": team.full_name,
                "abbreviation": team.abbreviation,
                "city": team.city,
                "name": team.name,
                "conference": team.conference
            }
            for team in teams
        ]
        
        return jsonify(team_list)
    except Exception as e:
        print(f"Error fetching teams: {str(e)}")
        return jsonify({
            'error': True,
            'message': f'Failed to load teams: {str(e)}'
        }), 500

@app.route('/api/games', methods=['GET'])
def get_games():
    """Get NBA games for a specific date from database."""
    try:
        # Get date from query parameters, default to today
        game_date_str = request.args.get('date', datetime.now().strftime('%m/%d/%Y'))
        
        # Convert to proper date format for database query
        try:
            game_date_obj = datetime.strptime(game_date_str, '%m/%d/%Y').date()
        except ValueError:
            # Try other format
            game_date_obj = datetime.strptime(game_date_str, '%Y-%m-%d').date()
        
        # Query games from database
        games = db.session.query(Game).filter(Game.game_date == game_date_obj).all()
        
        games_data = []
        
        for game in games:
            # Get team info
            home_team = Team.query.get(game.home_team_id)
            visitor_team = Team.query.get(game.visitor_team_id)
            
            if not home_team or not visitor_team:
                continue
            
            games_data.append({
                'game_id': game.id,
                'home_team': {
                    'id': home_team.id,
                    'name': home_team.full_name,
                    'abbreviation': home_team.abbreviation,
                    'score': game.home_team_score
                },
                'visitor_team': {
                    'id': visitor_team.id,
                    'name': visitor_team.full_name,
                    'abbreviation': visitor_team.abbreviation,
                    'score': game.visitor_team_score
                },
                'status': {
                    'id': game.status_id,
                    'text': game.status_text
                },
                'game_time': game.game_time
            })
        
        return jsonify({
            'games': games_data,
            'date': game_date_str
        })
        
    except Exception as e:
        print(f"Error fetching games: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'games': []
        }), 500

@app.route('/api/standings')
def get_standings():
    """Get current NBA standings from database"""
    try:
        # Query teams with their stats, ordered by conference and rank
        standings_query = db.session.query(
            Team.id,
            Team.full_name,
            Team.abbreviation,
            Team.conference,
            TeamStats.wins,
            TeamStats.losses,
            TeamStats.win_pct,
            TeamStats.conference_rank,
            TeamStats.points_per_game,
            TeamStats.rebounds_per_game,
            TeamStats.assists_per_game
        ).join(TeamStats, Team.id == TeamStats.team_id).order_by(
            Team.conference,
            TeamStats.conference_rank
        )
        
        standings = []
        for row in standings_query.all():
            standings.append({
                'id': row.id,
                'TeamName': row.full_name,
                'abbreviation': row.abbreviation,
                'Conference': row.conference,
                'ConferenceRank': row.conference_rank,
                'WINS': row.wins,
                'LOSSES': row.losses,
                'WinPercentage': row.win_pct,
                'full_name': row.full_name
            })
        
        return jsonify(standings)
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error in standings API: {str(e)}\n{error_details}")
        
        return jsonify({
            'error': True,
            'message': f'Failed to load standings data: {str(e)}'
        }), 500

@app.route('/teams')
def teams_page():
    """Render the teams page with standings data from database."""
    try:
        # Query teams with their stats for Eastern Conference
        eastern_teams_query = db.session.query(
            Team.id,
            Team.full_name,
            Team.abbreviation,
            TeamStats.wins,
            TeamStats.losses,
            TeamStats.win_pct,
            TeamStats.conference_rank
        ).join(TeamStats, Team.id == TeamStats.team_id).filter(
            Team.conference == 'East'
        ).order_by(TeamStats.conference_rank)
        
        # Query teams with their stats for Western Conference
        western_teams_query = db.session.query(
            Team.id,
            Team.full_name,
            Team.abbreviation,
            TeamStats.wins,
            TeamStats.losses,
            TeamStats.win_pct,
            TeamStats.conference_rank
        ).join(TeamStats, Team.id == TeamStats.team_id).filter(
            Team.conference == 'West'
        ).order_by(TeamStats.conference_rank)
        
        eastern_teams = []
        for row in eastern_teams_query.all():
            eastern_teams.append({
                'id': row.id,
                'full_name': row.full_name,
                'abbreviation': row.abbreviation,
                'wins': row.wins,
                'losses': row.losses,
                'win_pct': row.win_pct,
                'conference_rank': row.conference_rank
            })
        
        western_teams = []
        for row in western_teams_query.all():
            western_teams.append({
                'id': row.id,
                'full_name': row.full_name,
                'abbreviation': row.abbreviation,
                'wins': row.wins,
                'losses': row.losses,
                'win_pct': row.win_pct,
                'conference_rank': row.conference_rank
            })
        
        # Get last updated time
        refresh_tracker = RefreshTracker.query.filter_by(entity='standings').first()
        last_updated = refresh_tracker.last_refresh if refresh_tracker else None
        
        return render_template('teams.html', 
                             eastern_teams=eastern_teams,
                             western_teams=western_teams,
                             last_updated=last_updated)
        
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error rendering teams page: {str(e)}\n{error_details}")
        
        return render_template('teams.html', 
                             eastern_teams=[],
                             western_teams=[],
                             last_updated=None)

@app.route('/team/<int:team_id>')
def team_page(team_id):
    """Render the team page with detailed information."""
    try:
        print(f"Debug: Accessing team page for team_id: {team_id}")
        
        # Get team info from database
        team = Team.query.get(team_id)
        if not team:
            print(f"Debug: No team found for team_id: {team_id}")
            return render_template('404.html', message=f"Team with ID {team_id} not found"), 404
        
        print(f"Debug: Team found: {team.full_name}")
        
        # Get team stats
        team_stats_db = TeamStats.query.filter_by(team_id=team_id).first()
        
        team_data = {
            'id': team.id,
            'full_name': team.full_name,
            'abbreviation': team.abbreviation,
            'conference': team.conference
        }
        
        # Create team stats object
        if team_stats_db:
            team_stats = {
                'wins': team_stats_db.wins,
                'losses': team_stats_db.losses,
                'win_pct': team_stats_db.win_pct,
                'points_per_game': team_stats_db.points_per_game,
                'rebounds_per_game': team_stats_db.rebounds_per_game,
                'assists_per_game': team_stats_db.assists_per_game
            }
        else:
            team_stats = {
                'wins': 0,
                'losses': 0,
                'win_pct': 0.0,
                'points_per_game': 0.0,
                'rebounds_per_game': 0.0,
                'assists_per_game': 0.0
            }
        
        # Get roster with stats
        roster_query = db.session.query(
            Player.id,
            Player.full_name,
            Player.jersey,
            Player.position,
            Player.height,
            Player.weight,
            PlayerStats.gp,
            PlayerStats.min_pg,
            PlayerStats.pts_pg,
            PlayerStats.oreb_pg,
            PlayerStats.dreb_pg,
            PlayerStats.reb_pg,
            PlayerStats.ast_pg,
            PlayerStats.stl_pg,
            PlayerStats.blk_pg,
            PlayerStats.to_pg,
            PlayerStats.pf_pg,
            PlayerStats.ast_to
        ).outerjoin(PlayerStats, Player.id == PlayerStats.player_id).filter(
            Player.team_id == team_id
        )
        
        roster = []
        for row in roster_query.all():
            roster.append({
                'name': row.full_name,
                'position': row.position or 'N/A',
                'jersey': row.jersey or 'N/A',
                'height': row.height or 'N/A',
                'weight': row.weight or 'N/A',
                'age': 'N/A',  # Age not stored in current schema
                'gp': row.gp or 0,
                'min': row.min_pg or 0.0,
                'ppg': row.pts_pg or 0.0,
                'oreb': row.oreb_pg or 0.0,
                'dreb': row.dreb_pg or 0.0,
                'rpg': row.reb_pg or 0.0,
                'apg': row.ast_pg or 0.0,
                'spg': row.stl_pg or 0.0,
                'bpg': row.blk_pg or 0.0,
                'to': row.to_pg or 0.0,
                'pf': row.pf_pg or 0.0,
                'ast_to': row.ast_to or 0.0
            })
        
        print(f"Debug: Found {len(roster)} players in roster")
        
        # Get upcoming games from database
        today = datetime.now().date()
        upcoming_games_query = db.session.query(Game).filter(
            ((Game.home_team_id == team_id) | (Game.visitor_team_id == team_id)) &
            (Game.game_date > today)
        ).order_by(Game.game_date).limit(5)
        
        upcoming_games = []
        for game in upcoming_games_query.all():
            is_home = game.home_team_id == team_id
            opponent_id = game.visitor_team_id if is_home else game.home_team_id
            opponent = Team.query.get(opponent_id)
            
            if opponent:
                upcoming_games.append({
                    'date': game.game_date.strftime('%b %d, %Y'),
                    'opponent': opponent.full_name,
                    'is_home': is_home,
                    'win_probability': 50  # Default - you can implement ML predictions
                })
        
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
        
        return render_template('500.html', 
                              message=f"Error loading team page: {str(e)}",
                              details=error_details), 500

@app.route('/api/team/<int:team_id>/roster')
def team_roster_api(team_id):
    """API endpoint to get team roster from database"""
    try:
        players = Player.query.filter_by(team_id=team_id).all()
        
        roster_data = []
        for player in players:
            roster_data.append({
                'PLAYER_ID': player.id,
                'PLAYER': player.full_name,
                'NUM': player.jersey,
                'POSITION': player.position,
                'HEIGHT': player.height,
                'WEIGHT': player.weight
            })
        
        return jsonify(roster_data)
        
    except Exception as e:
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500

@app.route('/api/team/<int:team_id>/games')
def team_games_api(team_id):
    """API endpoint to get team games from database"""
    try:
        count = int(request.args.get('count', 10))
        
        # Get recent games for the team (last 'count' games)
        games = db.session.query(Game).filter(
            (Game.home_team_id == team_id) | (Game.visitor_team_id == team_id)
        ).order_by(Game.game_date.desc()).limit(count).all()
        
        games_data = []
        for game in games:
            # Determine if team was home or away
            is_home = game.home_team_id == team_id
            opponent_id = game.visitor_team_id if is_home else game.home_team_id
            opponent = Team.query.get(opponent_id)
            
            games_data.append({
                'GAME_ID': game.id,
                'GAME_DATE': game.game_date.strftime('%Y-%m-%d'),
                'MATCHUP': f"{'vs' if is_home else '@'} {opponent.abbreviation if opponent else 'UNK'}",
                'WL': 'W' if (is_home and game.home_team_score > game.visitor_team_score) or 
                           (not is_home and game.visitor_team_score > game.home_team_score) else 'L'
                      if game.home_team_score is not None and game.visitor_team_score is not None else '',
                'PTS': game.home_team_score if is_home else game.visitor_team_score
            })
        
        return jsonify(games_data)
        
    except Exception as e:
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500

@app.route('/api/team/<int:team_id>/player-stats')
def player_stats_api(team_id):
    """API endpoint to get player stats for a team from database"""
    try:
        # Query players with their stats
        player_stats_query = db.session.query(
            Player.id,
            Player.full_name,
            Player.jersey,
            Player.position,
            Player.height,
            Player.weight,
            PlayerStats.gp,
            PlayerStats.min_pg,
            PlayerStats.pts_pg,
            PlayerStats.oreb_pg,
            PlayerStats.dreb_pg,
            PlayerStats.reb_pg,
            PlayerStats.ast_pg,
            PlayerStats.stl_pg,
            PlayerStats.blk_pg,
            PlayerStats.to_pg,
            PlayerStats.pf_pg,
            PlayerStats.ast_to
        ).outerjoin(PlayerStats, Player.id == PlayerStats.player_id).filter(
            Player.team_id == team_id
        )
        
        player_stats = []
        for row in player_stats_query.all():
            player_stats.append({
                'PLAYER': row.full_name,
                'PLAYER_ID': row.id,
                'NUM': row.jersey,
                'POSITION': row.position,
                'HEIGHT': row.height,
                'WEIGHT': row.weight,
                'GP': row.gp or 0,
                'MIN': row.min_pg or 0.0,
                'PTS': row.pts_pg or 0.0,
                'OREB': row.oreb_pg or 0.0,
                'DREB': row.dreb_pg or 0.0,
                'REB': row.reb_pg or 0.0,
                'AST': row.ast_pg or 0.0,
                'STL': row.stl_pg or 0.0,
                'BLK': row.blk_pg or 0.0,
                'TO': row.to_pg or 0.0,
                'PF': row.pf_pg or 0.0,
                'AST_TO': row.ast_to or 0.0
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

# Background refresh endpoint (optional - for manual refresh)
@app.route('/api/refresh/<entity>')
def refresh_data(entity):
    """Manually refresh specific data"""
    try:
        if entity == 'teams':
            fetch_and_store_teams()
        elif entity == 'standings':
            fetch_and_store_standings()
        elif entity == 'games':
            fetch_and_store_games()
        elif entity.startswith('team_'):
            team_id = int(entity.split('_')[1])
            fetch_and_store_team_stats(team_id)
            fetch_and_store_team_roster(team_id)
        else:
            return jsonify({'error': 'Unknown entity'}), 400
        
        return jsonify({'success': True, 'message': f'Refreshed {entity}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)