# populate_database.py - Script to populate your database with NBA data
import os
import sys
from datetime import datetime

# Make sure we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import app, db, Team, TeamStats, Player, PlayerStats, Game
from data_fetcher import (
    initialize_database, 
    fetch_and_store_teams,
    fetch_and_store_standings,
    fetch_and_store_games,
    fetch_and_store_team_roster,
    fetch_and_store_team_stats,
    update_team_conferences,
    refresh_all_team_data,
    update_player_stats_only,
    update_team_player_stats_only
)

def show_player_stats_sample(team_id=None, limit=5):
    """Show a sample of player stats to verify updates"""
    try:
        query = db.session.query(Player, PlayerStats).join(PlayerStats, Player.id == PlayerStats.player_id)
        
        if team_id:
            query = query.filter(Player.team_id == team_id)
            team = Team.query.get(team_id)
            print(f"\n📊 Sample Player Stats for {team.full_name if team else 'Team ' + str(team_id)}:")
        else:
            print(f"\n📊 Sample Player Stats (Top {limit}):")
        
        players_with_stats = query.order_by(PlayerStats.pts_pg.desc()).limit(limit).all()
        
        if not players_with_stats:
            print("No player stats found")
            return
        
        print("-" * 80)
        print(f"{'Player':<25} {'Team':<5} {'GP':<3} {'MIN':<5} {'PTS':<5} {'REB':<5} {'AST':<5}")
        print("-" * 80)
        
        for player, stats in players_with_stats:
            team = Team.query.get(player.team_id)
            team_abbr = team.abbreviation if team else 'N/A'
            print(f"{player.full_name:<25} {team_abbr:<5} {stats.gp:<3} {stats.min_pg:<5.1f} {stats.pts_pg:<5.1f} {stats.reb_pg:<5.1f} {stats.ast_pg:<5.1f}")
        
    except Exception as e:
        print(f"❌ Error showing player stats: {str(e)}")

def update_players_by_team_name(team_name, season='2024-25'):
    """Update player stats for a team by team name (e.g., 'Los Angeles Lakers')"""
    try:
        team = Team.query.filter(Team.full_name.ilike(f'%{team_name}%')).first()
        if not team:
            print(f"Team matching '{team_name}' not found")
            
            # Show available teams
            print("\nAvailable teams:")
            teams = Team.query.all()
            for t in teams:
                print(f"  • {t.full_name} (ID: {t.id})")
            return False
        
        print(f"Found team: {team.full_name}")
        return update_team_player_stats_only(team.id, season)
        
    except Exception as e:
        print(f"❌ Error updating player stats for {team_name}: {str(e)}")
        return False

def main():
    """Main function to populate database"""
    print("🏀 NBA Database Population Script")
    print("=" * 40)
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("✓ Tables created/verified")
        
        # Check if database is empty
        team_count = Team.query.count()
        print(f"Current teams in database: {team_count}")
        
        if team_count == 0:
            print("\n📥 Database is empty. Running full initialization...")
            if initialize_database():
                print("✓ Database initialized successfully!")
            else:
                print("❌ Database initialization failed!")
                return
        else:
            print("\n🔄 Database has data. Choose what to update:")
            print("1. Update teams")
            print("2. Update standings")  
            print("3. Update today's games")
            print("4. Update specific team roster (Lakers)")
            print("5. Update all team data (WARNING: This takes a long time!)")
            print("6. Fix team conferences")
            print("7. Update player stats only (Lakers)")
            print("8. Update player stats by team name")
            print("9. Show sample player stats")
            
            choice = input("\nEnter your choice (1-9): ").strip()
            
            if choice == "1":
                print("\n📥 Updating teams...")
                if fetch_and_store_teams():
                    print("✓ Teams updated!")
                else:
                    print("❌ Failed to update teams")
                    
            elif choice == "2":
                print("\n📥 Updating standings...")
                if fetch_and_store_standings():
                    print("✓ Standings updated!")
                else:
                    print("❌ Failed to update standings")
                    
            elif choice == "3":
                print("\n📥 Updating today's games...")
                if fetch_and_store_games():
                    print("✓ Games updated!")
                else:
                    print("❌ Failed to update games")
                    
            elif choice == "4":
                lakers_id = 1610612747
                print(f"\n📥 Updating Lakers roster (ID: {lakers_id})...")
                if fetch_and_store_team_roster(lakers_id):
                    print("✓ Lakers roster updated!")
                else:
                    print("❌ Failed to update Lakers roster")
                    
            elif choice == "5":
                confirm = input("⚠️  This will update ALL team data and may take 30+ minutes. Continue? (y/N): ")
                if confirm.lower() == 'y':
                    print("\n📥 Updating all team data...")
                    if refresh_all_team_data():
                        print("✓ All team data updated!")
                    else:
                        print("❌ Failed to update all team data")
                else:
                    print("Operation cancelled.")
                    
            elif choice == "6":
                print("\n🔧 Fixing team conferences...")
                if update_team_conferences():
                    print("✓ Team conferences fixed!")
                else:
                    print("❌ Failed to fix team conferences")
                    
            elif choice == "7":
                lakers_id = 1610612747
                print(f"\n📊 Updating Lakers player stats only (ID: {lakers_id})...")
                if update_team_player_stats_only(lakers_id):
                    print("✓ Lakers player stats updated!")
                    show_player_stats_sample(lakers_id)
                else:
                    print("❌ Failed to update Lakers player stats")
                    
            elif choice == "8":
                team_name = input("Enter team name (e.g., 'Lakers', 'Warriors', 'Celtics'): ").strip()
                if team_name:
                    print(f"\n📊 Updating player stats for teams matching '{team_name}'...")
                    if update_players_by_team_name(team_name):
                        print("✓ Player stats updated!")
                        # Try to show sample
                        team = Team.query.filter(Team.full_name.ilike(f'%{team_name}%')).first()
                        if team:
                            show_player_stats_sample(team.id)
                    else:
                        print("❌ Failed to update player stats")
                else:
                    print("No team name provided")
                    
            elif choice == "9":
                show_all = input("Show top players from all teams? (y/N): ").lower() == 'y'
                if show_all:
                    show_player_stats_sample(limit=10)
                else:
                    team_name = input("Enter team name (or press Enter for Lakers): ").strip()
                    if not team_name:
                        team_name = "Lakers"
                    
                    team = Team.query.filter(Team.full_name.ilike(f'%{team_name}%')).first()
                    if team:
                        show_player_stats_sample(team.id, limit=10)
                    else:
                        print(f"Team matching '{team_name}' not found")
                        
            else:
                print("Invalid choice!")
        
        # Show final statistics
        print("\n📊 Database Statistics")
        print("-" * 30)
        
        team_count = Team.query.count()
        team_stats_count = TeamStats.query.count()
        player_count = Player.query.count()
        player_stats_count = PlayerStats.query.count()
        game_count = Game.query.count()
        
        print(f"Teams: {team_count}")
        print(f"Team Stats: {team_stats_count}")
        print(f"Players: {player_count}")
        print(f"Player Stats: {player_stats_count}")
        print(f"Games: {game_count}")
        
        # Show sample data
        if team_count > 0:
            print("\n🏀 Sample Teams:")
            sample_teams = Team.query.limit(5).all()
            for team in sample_teams:
                print(f"  • {team.full_name} ({team.abbreviation}) - {team.conference}")
        
        if game_count > 0:
            print("\n🏀 Recent Games:")
            recent_games = Game.query.order_by(Game.game_date.desc()).limit(3).all()
            for game in recent_games:
                home_team = Team.query.get(game.home_team_id)
                visitor_team = Team.query.get(game.visitor_team_id)
                if home_team and visitor_team:
                    score_info = ""
                    if game.home_team_score is not None and game.visitor_team_score is not None:
                        score_info = f" ({visitor_team.abbreviation} {game.visitor_team_score} - {game.home_team_score} {home_team.abbreviation})"
                    print(f"  • {game.game_date}: {visitor_team.full_name} @ {home_team.full_name}{score_info}")

def quick_test():
    """Quick test to verify database connectivity and basic functionality"""
    print("🧪 Quick Database Test")
    print("=" * 20)
    
    with app.app_context():
        try:
            # Test database connection
            team_count = Team.query.count()
            print(f"✓ Database connected. Teams in DB: {team_count}")
            
            # Test a simple fetch
            if team_count == 0:
                print("Database is empty. Run main() to populate.")
            else:
                # Show a sample team
                sample_team = Team.query.first()
                print(f"✓ Sample team: {sample_team.full_name}")
                
                # Check if team has stats
                team_stats = TeamStats.query.filter_by(team_id=sample_team.id).first()
                if team_stats:
                    print(f"✓ Team stats found: {team_stats.wins}W-{team_stats.losses}L")
                else:
                    print("- No team stats found")
                
                # Check players
                player_count = Player.query.filter_by(team_id=sample_team.id).count()
                print(f"✓ Players in {sample_team.abbreviation}: {player_count}")
                
                # Check player stats
                player_stats_count = db.session.query(PlayerStats).join(Player).filter(Player.team_id == sample_team.id).count()
                print(f"✓ Player stats in {sample_team.abbreviation}: {player_stats_count}")
                
                if player_stats_count > 0:
                    show_player_stats_sample(sample_team.id, limit=3)
            
        except Exception as e:
            print(f"❌ Database test failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        quick_test()
    else:
        main()