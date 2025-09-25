from flask import Flask, render_template, request, jsonify, send_file
import json
import os
from datetime import datetime

app = Flask(__name__)

# Player data
PLAYERS = {
    4: "Ryder", 5: "Sebastian", 6: "Hudson", 11: "Juna",
    12: "Bowen", 13: "Cole", 14: "Leo", 16: "Shea",
    20: "Pierre", 29: "Matthew", 35: "Carter", 37: "Slade",
    38: "Andrew", 39: "Ryland", 41: "Asher", 44: "Brooks"
}

STATS_FILE = 'hockey_stats.json'


def load_stats():
    """Load stats from file or create default"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('stats', create_default_stats())
        except:
            pass
    return create_default_stats()


def create_default_stats():
    """Create default stats structure"""
    return {
        str(num): {
            "plus_minus": 0,
            "blocked_shots": 0,
            "takeaways": 0
        } for num in PLAYERS.keys()
    }


def save_stats(stats):
    """Save stats to file"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "players": PLAYERS,
        "stats": stats
    }
    with open(STATS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


@app.route('/')
def index():
    """Main page"""
    stats = load_stats()
    return render_template('index.html', players=PLAYERS, stats=stats)


@app.route('/api/update_stat', methods=['POST'])
def update_stat():
    """Update a player's stat"""
    data = request.get_json()
    player_num = str(data['player_num'])
    stat_type = data['stat_type']
    change = int(data['change'])

    stats = load_stats()
    current_val = stats[player_num][stat_type]
    new_val = current_val + change

    # Don't let non-plus/minus stats go below 0
    if stat_type != "plus_minus":
        new_val = max(0, new_val)

    stats[player_num][stat_type] = new_val
    save_stats(stats)

    return jsonify({
        'success': True,
        'new_value': new_val,
        'player_num': player_num,
        'stat_type': stat_type
    })


@app.route('/api/reset_stats', methods=['POST'])
def reset_stats():
    """Reset all stats to zero"""
    stats = create_default_stats()
    save_stats(stats)
    return jsonify({'success': True, 'stats': stats})


@app.route('/api/get_stats')
def get_stats():
    """Get current stats"""
    stats = load_stats()
    return jsonify({'stats': stats, 'players': PLAYERS})


@app.route('/api/export_summary')
def export_summary():
    """Export stats summary as text file"""
    stats = load_stats()

    # Create summary text
    lines = []
    lines.append("HOCKEY DEFENSIVE STATS SUMMARY")
    lines.append("=" * 50)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append(f"{'Player':<15} {'Plus/Minus':<12} {'Blocked':<8} {'Takeaways':<10}")
    lines.append("-" * 50)

    for player_num in sorted([int(k) for k in stats.keys()]):
        name = f"#{player_num} {PLAYERS[player_num]}"
        player_stats = stats[str(player_num)]
        lines.append(
            f"{name:<15} {player_stats['plus_minus']:<12} {player_stats['blocked_shots']:<8} {player_stats['takeaways']:<10}")

    # Calculate totals
    total_blocks = sum(stats[str(p)]["blocked_shots"] for p in PLAYERS.keys())
    total_takeaways = sum(stats[str(p)]["takeaways"] for p in PLAYERS.keys())
    total_pm = sum(stats[str(p)]["plus_minus"] for p in PLAYERS.keys())

    lines.append("-" * 50)
    lines.append(f"{'TOTALS':<15} {total_pm:<12} {total_blocks:<8} {total_takeaways:<10}")

    # Write to file
    filename = f"hockey_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))

    return send_file(filename, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5015)