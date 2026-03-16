# Code Analysis: Hockey Stats App

**Date:** 2026-03-16

## Architecture Summary
Single-file Flask app (`app.py`, 410 lines) with 3 SQLAlchemy models (Player, Game, GameStat), 8 routes, SQLite storage, deployed on Fly.io with persistent volume. Templates extend `base.html`.

---

## Issues Found

### Security

1. **XSS in `linkify` filter** (`app.py:16-18`)
   The regex replacement injects user-supplied URL text directly into an `<a>` tag without escaping. A URL containing `"` could break out of the `href` attribute. Should use `markupsafe.escape()` on the URL before inserting it into HTML.

2. **Hardcoded default secret key** (`app.py:31`)
   `SECRET_KEY` defaults to `'your-secret-key-here'` when the env var isn't set. Fine for local dev, dangerous if production ever falls through to the default.

### Dead Code

3. **`static/script.js` references non-existent API routes** (`script.js:31,44,136,189`)
   Calls `/api/get_stats`, `/api/update_stat`, `/api/reset_stats`, `/api/export_summary` — none exist in `app.py`. This file is never loaded by any template. Can be deleted.

4. **`static/style.css` has unused classes** (`style.css:162-267`)
   `.stats-grid` (grid layout), `.header-row`, `.player-row`, `.stat-cell`, `.cell`, `.player-info`, `.totals-section` — defined but unused in templates. Written for an earlier UI.

5. **`create_app()` factory never called** (`app.py:401-403`)
   `init_db()` is called at module level (line 407), Gunicorn imports `app:app`. The factory is dead code.

### Performance

6. **N+1 query in `build_games_list()`** (`app.py:91`)
   Each iteration calls `GameStat.query.filter_by(game_date=gdate).count()` per game. Could batch with a single `GROUP BY` query.

7. **`get_total_stats()` uses Python-side aggregation** (`app.py:43-59`)
   Loads all GameStat rows per player into memory and sums in Python. A SQL aggregate (`db.func.sum`) would be more efficient at scale.

### Code Quality

8. **Debug print statements in production** (`app.py:221,232`)
   `print(f"DEBUG: ...")` left in code. Should be removed or converted to `logging`.

9. **Bare `except Exception` blocks** (`app.py:205,345,360,395`)
   Several routes catch all exceptions silently, masking bugs. Should at minimum log the exception.

10. **Duplicate hidden player list** (`app.py:146,179`)
    `hidden_players = ['Leo', 'Hudson']` defined in both `index()` and `record_game()`. Should be a module-level constant.

11. **Dynamic `type()` for placeholder objects** (`app.py:309`)
    `type('obj', (object,), {...})()` is used instead of a simple dataclass or namedtuple.

12. **Inconsistent element ID naming** (`record_game.html`)
    JS references both `players-summary`/`autosave-status` (kebab-case) and `playersSummary`/`autosaveStatus` (camelCase); the camelCase IDs don't exist in the HTML.

13. **Conditional CSS loading** (`index.html:6`, `games.html:6`)
    `style.css` loaded with `media="(max-width: 768px)"` — desktop browsers won't apply it. Relies on `base.html` inline styles for desktop, which is fragile.

---

## What's Working Well
- Clean upsert logic in `save_game_stats` — handles create/update/delete correctly
- Good mobile-first responsive design with dual desktop/mobile layouts
- Autosave with 500ms debounce is solid UX
- Docker + Fly.io deployment well-configured with persistent volume mount
- Schema auto-creation with player seeding is clean
- Bulk delete with select-all in games list is well-implemented
