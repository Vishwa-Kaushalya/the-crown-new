# The Crown — Debate Tournament Dashboard

A full-featured debate tournament management system built with **Flask** and **Tailwind CSS**. Designed for British Parliamentary (BP) and similar formats, The Crown handles everything from candidate registration and scoring through to outrounds, motion reveals, and archived Hall of Fame records.

---

## Features

### Public Views
| Page | Route | Description |
|---|---|---|
| Leaderboard | `/` | Live ranked standings with marks bar, rank-glow highlights, and a Chart.js prelim-points chart |
| Matches | `/matches` | All prelim rounds and outround matchups with status indicators |
| Live Dashboard | `/live` | Real-time view intended for display screens |
| Candidate Profile | `/candidate/<name>` | Per-speaker round history and stats |
| Timer | `/timer` | Official debate speech timer with admin-managed presets |
| Hall of Fame | `/hall_of_fame` | Archived past tournaments |
| Motion Reveal Kiosk | `/reveal_kiosk` | Fullscreen motion reveal display (opens in new tab) |

### Admin Panel
| Page | Route | Description |
|---|---|---|
| Registration | `/admin/registration` | Register candidates and create outround teams |
| Score Entry | `/admin/score/<match_id>` | Submit speaker scores for a prelim match |
| Outround Scoring | `/admin/score_outround/<match_id>` | Submit outround results |
| Motions Vault | `/admin/motions` | Draft, publish, and trigger motion reveals |
| Settings | `/admin/settings` | Manage tournament workspaces and archives |
| User Management | `/admin/users` | Add/remove admin accounts (master admin only) |
| Audit Log | `/admin/audit` | Full action history with print view |

---

## Architecture

```
the-crown-new/
├── app.py                  # Flask application (all routes and business logic)
├── requirements.txt        # Python dependencies
├── templates/              # Jinja2 HTML templates
│   ├── index.html          # Leaderboard
│   ├── matches.html        # Matches list
│   ├── live_dashboard.html # Live display
│   ├── timer.html          # Speech timer
│   ├── candidate_profile.html
│   ├── hall_of_fame.html / hall_of_fame_view.html
│   ├── reveal_kiosk.html / motion_reveal.html
│   ├── admin_registration.html
│   ├── admin_settings.html
│   ├── admin_users.html
│   ├── audit_log.html / audit_print.html
│   ├── motions.html
│   ├── score.html / outround_score.html
│   ├── matches.html / leaderboard_outrounds.html
│   └── match_poster.html
├── static/                 # Static assets
└── data/                   # JSON data store (auto-created on first run)
    ├── tournaments_index.json
    ├── tournaments/        # Per-tournament data files
    ├── archives_index.json
    ├── archives/           # Archived tournament snapshots
    ├── admins.json
    ├── motions.json
    ├── timer.json
    └── audit_log.json
```

### Data Model
All tournament data is stored as JSON. Each active tournament has its own workspace file containing:
- **Candidates** — speaker details, round scores (R1–R6), win count, alias, avatar
- **Rounds** — match records with teams, sides, and results
- **OutroundTeams** — paired teams for elimination rounds

The system auto-migrates legacy `master_data.json` data into the tournament workspace on first run.

### Ranking Logic
Candidates are sorted into two groups:
1. **Group A** — 4+ wins, sorted by total prelim marks (descending)
2. **Group B** — fewer than 4 wins, sorted by total prelim marks (descending)

Group A always ranks above Group B. The top 16 qualify for outrounds.

---

## Setup

**Requirements:** Python 3.9+

```bash
pip install -r requirements.txt
python app.py
```

The app starts on **`http://0.0.0.0:5001`**.

On first run the `data/` directory and a default tournament workspace are created automatically.

### Default Admin
Create admin accounts via the `/admin/register_admin` endpoint. The first account registered with master privileges gains access to Settings, User Management, and Audit Logs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask 3.0 · Werkzeug |
| Templating | Jinja2 |
| Styling | Tailwind CSS (CDN) |
| Charts | Chart.js (CDN) |
| Fonts | Playfair Display · Inter · JetBrains Mono |
| Storage | JSON flat files |

---

## Recent Changes

### UI Redesign (May 2026)
A comprehensive visual overhaul was applied across the Leaderboard and Matches pages:

- **Deeper background** — base colour updated from `#0f172a` to `#080c14` for a richer dark canvas
- **Noise texture overlay** — subtle SVG fractal-noise layer adds film-grain depth
- **Ambient blob lighting** — soft amber and indigo radial glows behind the content area
- **Refined glass morphism** — increased blur (`20px`) and updated border opacity on `.glass` cards
- **JetBrains Mono** added for alias tags and monospace data
- **Slimmer top navigation** — height reduced from `h-16` to `h-14`; inline nav links (Leaderboard · Matches · Live) added directly to the navbar on `sm+` screens
- **SVG icons in sidebar** — emoji icons replaced with inline SVG for timer and Hall of Fame links
- **Rank-level row styling** — dedicated CSS classes (`row-rank-1`, `row-rank-2`, `row-rank-3`, `row-top16`) for gold/silver/bronze/qualifier highlights
- **Marks progress bar** — thin amber gradient bar shows each speaker's score relative to the maximum
- **Pip activity indicators** — small green/grey dots represent round-by-round participation
- **Live pulse dot** — animated green dot on the Live nav link and leaderboard hero
- **Hero section** — new stats block on the leaderboard showing total candidates, qualified count, and live status
- **Chart resized** — performance chart height reduced (`180px` / `240px` sm breakpoint) for a cleaner layout
- **Row entrance animation** (`rowUp`) and hero fade-in (`heroFade`)
- **Matches page** — pending matches now animate with a subtle amber pulse (`pendingPulse`); completed matches show a green left border; modal entry animation smoothed

### Port Change
The development server now runs on **port 5001** (previously 5000).
