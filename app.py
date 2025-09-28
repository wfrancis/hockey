from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))

# Use persistent storage path in production, local path in development
if os.getenv('FLASK_ENV') == 'production':
    db_path = '/app/data/hockey_stats.db'
else:
    db_path = os.path.join(basedir, "hockey_stats.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')

db = SQLAlchemy(app)


# Database Models
class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    stats = db.relationship('GameStat', backref='player', lazy=True, cascade='all, delete-orphan')

    def get_total_stats(self):
        """Calculate total stats across all games"""
        total_plus_minus = sum(stat.plus_minus for stat in self.stats)
        total_blocked_shots = sum(stat.blocked_shots for stat in self.stats)
        total_takeaways = sum(stat.takeaways for stat in self.stats)
        total_shots_taken = sum(stat.shots_taken for stat in self.stats)
        games_played = len(self.stats)

        return {
            'plus_minus': total_plus_minus,
            'blocked_shots': total_blocked_shots,
            'takeaways': total_takeaways,
            'shots_taken': total_shots_taken,
            'games_played': games_played
        }


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.DateTime, unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=True)


class GameStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    game_date = db.Column(db.DateTime, default=datetime.utcnow)
    plus_minus = db.Column(db.Integer, default=0)
    blocked_shots = db.Column(db.Integer, default=0)
    takeaways = db.Column(db.Integer, default=0)
    shots_taken = db.Column(db.Integer, default=0)


def build_games_list():
    """Build list of saved games from Game table and distinct GameStat dates."""
    games_map = {g.game_date: g for g in Game.query.all()}
    # distinct dates from GameStat
    distinct_dates = [row[0] for row in db.session.query(GameStat.game_date).distinct().all()]
    all_dates = set(list(games_map.keys()) + distinct_dates)

    games_list = []
    for gdate in all_dates:
        if not gdate:
            continue
        name = games_map.get(gdate).name if gdate in games_map else None
        entries_count = GameStat.query.filter_by(game_date=gdate).count()
        games_list.append({
            'game_date': gdate,
            'date_str': gdate.strftime('%Y-%m-%d %I:%M %p'),
            'date_iso': gdate.strftime('%Y-%m-%dT%H:%M'),
            'name': name or '',
            'entries_count': entries_count
        })

    games_list.sort(key=lambda x: x['game_date'], reverse=True)
    return games_list


# Initialize database and add players
def init_db():
    with app.app_context():
        db.create_all()

        # Player roster
        players_data = [
            (4, 'Ryder'),
            (5, 'Sebastian'),
            (6, 'Hudson'),
            (11, 'Juna'),
            (12, 'Bowen'),
            (13, 'Cole'),
            (14, 'Leo'),
            (16, 'Shea'),
            (20, 'Pierre'),
            (29, 'Matthew'),
            (35, 'Carter'),
            (37, 'Slade'),
            (38, 'Andrew'),
            (39, 'Ryland'),
            (41, 'Asher'),
            (44, 'Brooks')
        ]

        # Only add players if they don't exist
        for number, name in players_data:
            if not Player.query.filter_by(number=number).first():
                player = Player(number=number, name=name)
                db.session.add(player)

        db.session.commit()


# Routes
@app.route('/')
def index():
    """Main dashboard showing all players and their total stats"""
    players = Player.query.order_by(Player.number).all()
    player_stats = []

    for player in players:
        stats = player.get_total_stats()
        player_stats.append({
            'id': player.id,
            'number': player.number,
            'name': player.name,
            'stats': stats
        })

    return render_template('index.html', players=player_stats)


@app.route('/record_game')
def record_game():
    """Page to record stats for a new game"""
    players = Player.query.order_by(Player.number).all()
    initial_date = request.args.get('date', '')
    initial_name = request.args.get('name', '')
    # If only date provided, try to prefill name from Game table
    if initial_date and not initial_name:
        try:
            parsed = datetime.fromisoformat(initial_date)
            g = Game.query.filter_by(game_date=parsed).first()
            if g and g.name:
                initial_name = g.name
        except Exception:
            pass
    return render_template('record_game.html', players=players,
                           initial_game_date=initial_date,
                           initial_game_name=initial_name)


@app.route('/save_game_stats', methods=['POST'])
def save_game_stats():
    """Save stats for a game"""
    data = request.json
    game_date = datetime.fromisoformat(data['game_date'])
    game_name = (data.get('game_name') or '').strip()

    try:
        any_nonzero = False
        for player_stat in data['players']:
            # Accept payloads that may omit fields other than plus_minus
            pm = int(player_stat.get('plus_minus', 0) or 0)
            bs = int(player_stat.get('blocked_shots', 0) or 0)
            tk = int(player_stat.get('takeaways', 0) or 0)
            st = int(player_stat.get('shots_taken', 0) or 0)

            # Find existing stat row for this player and game_date
            existing = GameStat.query.filter_by(player_id=player_stat['player_id'], game_date=game_date).first()

            if pm == 0 and bs == 0 and tk == 0 and st == 0:
                # If all zeros and a row exists, delete it (treat as cleared)
                if existing:
                    db.session.delete(existing)
                continue

            any_nonzero = True
            if existing:
                # Update existing row (upsert behavior)
                existing.plus_minus = pm
                existing.blocked_shots = bs
                existing.takeaways = tk
                existing.shots_taken = st
            else:
                # Insert new row
                stat = GameStat(
                    player_id=player_stat['player_id'],
                    game_date=game_date,
                    plus_minus=pm,
                    blocked_shots=bs,
                    takeaways=tk,
                    shots_taken=st
                )
                db.session.add(stat)

        # Upsert Game record (store name if provided, or just ensure a game row exists when stats exist)
        game = Game.query.filter_by(game_date=game_date).first()
        if game:
            if game_name:
                game.name = game_name
        else:
            if game_name or any_nonzero:
                game = Game(game_date=game_date, name=game_name or None)
                db.session.add(game)

        db.session.commit()
        message = 'Autosaved' if data.get('autosave') else 'Game stats saved successfully!'
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400


@app.route('/player/<int:player_id>')
def player_detail(player_id):
    """View detailed stats for a specific player"""
    player = Player.query.get_or_404(player_id)
    game_stats = GameStat.query.filter_by(player_id=player_id).order_by(GameStat.game_date.desc()).all()
    total_stats = player.get_total_stats()

    return render_template('player_detail.html',
                           player=player,
                           game_stats=game_stats,
                           total_stats=total_stats)


@app.route('/delete_stat/<int:stat_id>', methods=['POST'])
def delete_stat(stat_id):
    """Delete a specific game stat"""
    stat = GameStat.query.get_or_404(stat_id)
    player_id = stat.player_id
    db.session.delete(stat)
    db.session.commit()
    return redirect(url_for('player_detail', player_id=player_id))


@app.route('/delete_game', methods=['POST'])
def delete_game():
    """Delete an entire game (all stats for that date) and its Game record"""
    date_str = request.form.get('date', '')
    try:
        game_date = datetime.fromisoformat(date_str)
    except Exception:
        return redirect(url_for('index'))

    try:
        # Delete all stats for this game date
        stats = GameStat.query.filter_by(game_date=game_date).all()
        for s in stats:
            db.session.delete(s)

        # Delete the Game record if it exists
        game = Game.query.filter_by(game_date=game_date).first()
        if game:
            db.session.delete(game)

        db.session.commit()
    except Exception:
        db.session.rollback()

    return redirect(url_for('index'))


@app.route('/games')
def games():
    """List all recorded games with bulk actions"""
    games_list = build_games_list()
    return render_template('games.html', games=games_list)


@app.route('/delete_games_bulk', methods=['POST'])
def delete_games_bulk():
    """Bulk delete selected games given their ISO date strings."""
    date_strs = request.form.getlist('dates')
    try:
        for date_str in date_strs:
            try:
                game_date = datetime.fromisoformat(date_str)
            except Exception:
                continue

            # Delete all stats for this game date
            stats = GameStat.query.filter_by(game_date=game_date).all()
            for s in stats:
                db.session.delete(s)

            # Delete the Game record if it exists
            game = Game.query.filter_by(game_date=game_date).first()
            if game:
                db.session.delete(game)

        db.session.commit()
    except Exception:
        db.session.rollback()

    return redirect(url_for('games'))

# Initialize database on app startup
def create_app():
    """Factory function to create and configure app"""
    init_db()
    return app

# Ensure database is initialized when module is imported
init_db()

if __name__ == '__main__':
    app.run(debug=True)