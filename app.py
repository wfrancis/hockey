from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "hockey_stats.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'

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


class GameStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    game_date = db.Column(db.DateTime, default=datetime.utcnow)
    plus_minus = db.Column(db.Integer, default=0)
    blocked_shots = db.Column(db.Integer, default=0)
    takeaways = db.Column(db.Integer, default=0)
    shots_taken = db.Column(db.Integer, default=0)


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
    return render_template('record_game.html', players=players)


@app.route('/save_game_stats', methods=['POST'])
def save_game_stats():
    """Save stats for a game"""
    data = request.json
    game_date = datetime.fromisoformat(data['game_date'])

    try:
        for player_stat in data['players']:
            if any([player_stat['plus_minus'] != 0,
                    player_stat['blocked_shots'] != 0,
                    player_stat['takeaways'] != 0,
                    player_stat['shots_taken'] != 0]):
                stat = GameStat(
                    player_id=player_stat['player_id'],
                    game_date=game_date,
                    plus_minus=player_stat['plus_minus'],
                    blocked_shots=player_stat['blocked_shots'],
                    takeaways=player_stat['takeaways'],
                    shots_taken=player_stat['shots_taken']
                )
                db.session.add(stat)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Game stats saved successfully!'})
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


if __name__ == '__main__':
    init_db()
    app.run(debug=True)