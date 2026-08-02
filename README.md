# Project Sherlock 🕵️

A multilingual (UZ/EN/RU) Telegram detective game bot. Players get one educational
clue per day for a 5-day season, submit answers (max 3 attempts/clue), earn points,
climb a leaderboard, and keep a personal **Detective Journal** of every case they've
worked.

Built with: **Python 3.11+, aiogram 3.x, PostgreSQL, SQLAlchemy (async), Redis (FSM
storage), APScheduler (clue releases/reminders)**. Chosen because aiogram 3 gives
clean router-based handlers, native FSM, and async DB access scales well for a bot
that will grow seasons/teams/XP without a rewrite.

## Architecture

```
sherlock/
├── app/
│   ├── main.py                 # entrypoint, bot/dispatcher wiring
│   ├── config.py                # env-driven settings (pydantic-settings)
│   ├── database/
│   │   ├── engine.py             # async engine/session factory
│   │   └── models.py             # SQLAlchemy models (see schema below)
│   ├── localization/
│   │   ├── loader.py             # loads locale JSON, t(key, lang, **kwargs)
│   │   └── locales/{en,ru,uz}.json
│   ├── keyboards/
│   │   ├── main_menu.py          # persistent reply keyboard
│   │   └── inline.py             # inline keyboards (language, answer attempts, admin)
│   ├── middlewares/
│   │   ├── i18n.py               # injects user's language + t() into handlers
│   │   └── user.py               # ensures a User row exists, attaches to context
│   ├── services/
│   │   ├── answer_checker.py     # normalization + fuzzy/synonym matching
│   │   ├── scoring.py            # attempt -> points, season totals, tie-break
│   │   └── journal_service.py    # builds/reads the Detective Journal
│   ├── handlers/
│   │   ├── start.py              # /start, registration, language picker
│   │   ├── language.py           # /language
│   │   ├── play.py               # clue delivery + answer submission (FSM)
│   │   ├── journal.py            # /journal
│   │   ├── profile.py            # /profile, /myrank
│   │   ├── leaderboard.py        # /leaderboard
│   │   └── admin/
│   │       └── panel.py          # admin-only: seasons/clues/broadcast/export
│   └── utils/
│       └── logger.py
├── migrations/
│   └── 001_init.sql              # raw SQL schema (Alembic-ready structure)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Why this shape scales without code changes for new seasons

- **Seasons/Clues/Answers are pure data** (`seasons`, `clues` tables). A new season
  is an INSERT, not a deploy.
- **Localization is JSON**, not hardcoded strings — adding a 4th language means
  adding `locales/xx.json` + one entry in `config.py`.
- **Journal, Scoring, and Answer-checking are services**, decoupled from Telegram
  handlers — so a future web dashboard or admin API can reuse them untouched.
- **`clue_media_type` column** (text/image/audio/video/qr/location) is already in
  the schema so image/audio/video clues need zero migration later.

## Setup

```bash
cp .env.example .env         # fill in BOT_TOKEN, DATABASE_URL, ADMIN_IDS
docker compose up --build    # bot + postgres + redis
```

Or locally:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
psql $DATABASE_URL -f migrations/001_init.sql
python -m app.main
```

## Deployment (Railway/Render/VPS)

1. Provision a Postgres instance (Railway/Render both offer managed Postgres) and
   a Redis instance (used for FSM state — attempts-in-progress, admin wizards).
2. Set env vars from `.env.example` in the platform's dashboard.
3. Run `migrations/001_init.sql` against the managed DB once (`psql $DATABASE_URL -f migrations/001_init.sql`).
4. Point the platform's start command at `python -m app.main` (long-polling — no
   webhook/public URL needed). For VPS, run under `systemd` or `pm2` + this Docker
   image for restarts.

## Status

Core scaffold generated: registration + language selection, daily clue delivery,
attempt-based answer verification with scoring, Detective Journal, profile,
leaderboard, and an admin panel skeleton. Scheduler wiring for automatic daily
clue release/reminders is stubbed in `main.py` — plug in real release times once
Season 1 content is uploaded.
