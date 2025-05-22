# db.py - Database connection and schema setup using SQLAlchemy
import os
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app and database
app = Flask(__name__)

# Configure for MySQL instead of SQLite
app.config.update({
    'SQLALCHEMY_DATABASE_URI': f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}",
    'SQLALCHEMY_TRACK_MODIFICATIONS': False
})

db = SQLAlchemy(app)

# Models
class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    abbreviation = db.Column(db.String(10), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    conference = db.Column(db.String(20), nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class TeamStats(db.Model):
    __tablename__ = 'team_stats'
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), primary_key=True)
    wins = db.Column(db.Integer, default=0, nullable=False)
    losses = db.Column(db.Integer, default=0, nullable=False)
    win_pct = db.Column(db.Float, default=0, nullable=False)
    conference_rank = db.Column(db.Integer, default=0, nullable=False)
    points_per_game = db.Column(db.Float, default=0, nullable=False)
    rebounds_per_game = db.Column(db.Float, default=0, nullable=False)
    assists_per_game = db.Column(db.Float, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    jersey = db.Column(db.String(10))
    position = db.Column(db.String(20))
    height = db.Column(db.String(10))
    weight = db.Column(db.String(10))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class PlayerStats(db.Model):
    __tablename__ = 'player_stats'
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), primary_key=True)
    gp = db.Column(db.Integer, default=0, nullable=False)
    min_pg = db.Column(db.Float, default=0, nullable=False)
    pts_pg = db.Column(db.Float, default=0, nullable=False)
    oreb_pg = db.Column(db.Float, default=0, nullable=False)
    dreb_pg = db.Column(db.Float, default=0, nullable=False)
    reb_pg = db.Column(db.Float, default=0, nullable=False)
    ast_pg = db.Column(db.Float, default=0, nullable=False)
    stl_pg = db.Column(db.Float, default=0, nullable=False)
    blk_pg = db.Column(db.Float, default=0, nullable=False)
    to_pg = db.Column(db.Float, default=0, nullable=False)
    pf_pg = db.Column(db.Float, default=0, nullable=False)
    ast_to = db.Column(db.Float, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Game(db.Model):
    __tablename__ = 'games'
    id = db.Column(db.String(50), primary_key=True)
    home_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    visitor_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    game_date = db.Column(db.Date, nullable=False)
    game_time = db.Column(db.String(50))
    status_id = db.Column(db.Integer)
    status_text = db.Column(db.String(100))
    home_team_score = db.Column(db.Integer)
    visitor_team_score = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class RefreshTracker(db.Model):
    __tablename__ = 'refresh_tracker'
    entity = db.Column(db.String(100), primary_key=True)
    last_refresh = db.Column(db.DateTime, default=datetime.utcnow)

def should_refresh(entity, hours=6):
    tracker = RefreshTracker.query.filter_by(entity=entity).first()
    if not tracker:
        return True
    return datetime.utcnow() - tracker.last_refresh > timedelta(hours=hours)

def update_refresh_time(entity):
    now = datetime.utcnow()
    tracker = RefreshTracker.query.get(entity)
    if tracker:
        tracker.last_refresh = now
    else:
        tracker = RefreshTracker(entity=entity, last_refresh=now)
        db.session.add(tracker)
    db.session.commit()

def is_data_stale(table_cls, id_column=None, id_value=None, hours=6):
    query = table_cls.query
    if id_column and id_value:
        query = query.filter(getattr(table_cls, id_column) == id_value)
    record = query.first()
    if not record:
        return True
    return datetime.utcnow() - record.last_updated > timedelta(hours=hours)