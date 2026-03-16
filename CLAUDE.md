# Hockey Stats App - Development Guide

## Project Overview

Flask web app for tracking youth hockey team stats. SQLite database, deployed on Fly.io with persistent volume storage.

**Stack:** Python 3.11, Flask, Flask-SQLAlchemy, SQLite, Gunicorn, Docker, Fly.io

## Architecture

```
app.py              # All routes, models, and logic (single-file Flask app)
templates/          # Jinja2 templates (base.html, index.html, record_game.html, player_detail.html, games.html)
static/             # CSS (style.css) and JS (script.js)
hockey_stats.db     # Local dev SQLite database
fly.toml            # Fly.io deployment config
Dockerfile          # Production container
```

### Key Models
- **Player** — roster entry (number, name). Stats relationship via GameStat.
- **Game** — game date + optional name/label.
- **GameStat** — per-player per-game stats (plus_minus, blocked_shots, takeaways, shots_taken, shot_differential).

### Key Routes
- `/` — Dashboard with leaderboard sorted by plus/minus
- `/record_game` — Record or edit game stats (supports autosave)
- `/player/<id>` — Individual player stat history
- `/games` — Game list with bulk delete
- `/save_game_stats` (POST) — Upsert game stats via JSON
- `/delete_game` (POST) — Delete a game and all its stats

## Workflow

### 1. Plan Before Building
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan — don't keep pushing
- Write clear specs before touching code

### 2. Use Subagents
- Offload research, exploration, and parallel analysis to subagents
- Keep the main context window clean and focused
- One task per subagent for focused execution

### 3. Verify Before Done
- Never mark a task complete without proving it works
- Run the app, check routes, demonstrate correctness
- Ask: "Would a staff engineer approve this?"
- **All production testing happens on Fly.io** — deploy first, then test against the live server

### 4. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky, step back and implement the clean solution
- Skip this for simple, obvious fixes — don't over-engineer

### 5. Autonomous Bug Fixing
- When given a bug report: just fix it
- Point at logs, errors, failing behavior — then resolve
- Zero hand-holding required from the user

## Development

### Running Locally
```bash
pip install -r requirements.txt
python app.py
# App runs on http://localhost:5000 with debug=True
```

### Deploying
```bash
fly deploy
```

### Database
- **Local:** `hockey_stats.db` in project root
- **Production:** `/app/data/hockey_stats.db` on persistent Fly.io volume (`hockey_data` mount)
- Schema auto-creates on startup via `init_db()`
- Player roster is seeded automatically if missing

## Code Principles

- **Simplicity First:** This is a single-file Flask app. Keep it that way unless complexity truly demands splitting.
- **No Hardcoding:** Don't hardcode stats, player lists, or business logic that should come from the database.
- **Minimal Impact:** Changes should only touch what's necessary. Don't refactor adjacent code uninvited.
- **Find Root Causes:** No temporary fixes. If something is broken, fix it properly.
- **Preserve Data:** Never drop or reset the production database. Migrations must be additive.
- **Hidden Players:** Some players (Leo, Hudson) are filtered from display but remain in the DB. Respect this pattern.

## Git Commits

- Write clear, descriptive commit messages focused on the "why"
- **No Co-Authored-By** trailers — only the user's git config determines authorship
- Keep commits atomic — one logical change per commit

## Task Management

1. **Plan First:** Write a plan with checkable items before implementing
2. **Track Progress:** Mark items complete as you go
3. **Explain Changes:** High-level summary at each step
4. **Capture Lessons:** If corrected, note the pattern to avoid repeating it

## Common Pitfalls

- The `game_date` field is a DateTime used as a unique key for games — be careful with timezone handling
- `save_game_stats` does upsert logic: updates existing rows, inserts new ones, deletes zeroed-out rows
- The `linkify` Jinja filter auto-links URLs in text — keep it XSS-safe
- `build_games_list()` merges Game records and distinct GameStat dates — both sources matter
- Templates extend `base.html` — check there first for layout/style issues
