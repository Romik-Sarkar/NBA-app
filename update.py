# Quick script to refresh all team stats with the fix
from db import app, Team
from data_fetcher import fetch_and_store_team_stats

with app.app_context():
    teams = Team.query.all()
    for team in teams:
        print(f"Refreshing stats for {team.full_name}")
        fetch_and_store_team_stats(team.id)
