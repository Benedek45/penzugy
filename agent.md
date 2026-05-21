# 🤖 Agent Guide — [PROJECT_NAME]

This file is for AI coding assistants. Read it fully before touching any file.

---

## What This Project Is

A joke financial education web game. Player starts with virtual money, gambles it at
mini-games around a town hub, goes broke, gets a job, earns money back, repeats.
Tone: absurdist satire of capitalism. Educational second, funny first.

Stack: Python (Flask) backend + plain HTML/CSS/JS frontend. No framework.

---

## Project Structure

```
├── agent.md               ← you are here
├── app.py                 ← Flask server, all routes
├── requirements.txt       ← Python dependencies
├── images.jpg             ← decorative image
├── data/
│   └── hints.json         ← NPC financial term hints (term + explanation)
├── saves/                 ← player JSON save files (auto-created)
├── static/
│   ├── css/
│   │   └── style.css      ← shared styles, CSS variables, fonts
│   ├── js/
│   │   └── game.js        ← shared JS: GameAPI, EventBus, utilities
│   └── assets/            ← images, sprites (PNG)
├── templates/
│   ├── base.html           ← base Jinja2 template (head, nav, scripts)
│   ├── hub.html            ← main town map, clickable buildings
│   ├── login.html          ← name entry / new game / load game
│   └── games/              ← all game templates (GAMES + JOBS)
│       ├── _template.html  ← copy this to add a new mini-game / job
│       ├── casino.html
│       ├── horse_race.html
│       ├── stock_market.html
│       ├── slots.html
│       ├── chess.html
│       ├── cashier.html     ← job
│       ├── warehouse.html   ← job
│       ├── taxi.html        ← job
│       └── cook.html        ← job
```

---

## Flask Session State

The Flask session is the single source of truth for live game state.

```python
session = {
    "player_name": str,
    "balance":     int,   # current money (can go negative = debt)
    "debt":        int,   # total outstanding debt
    "stats": {
        "games_played":  int,
        "bribes_used":   int,
        "times_employed": int,
        "biggest_win":   int,
        "biggest_loss":  int,
    }
}
```

Never read/write save files during gameplay. Save files are only touched on:
- Explicit "Save Game" button → `POST /api/save`
- Page load with returning player → `GET /api/load/<name>`

---

## API Endpoints

All return `Content-Type: application/json`.

| Method | Route | Body / Params | Returns |
|--------|-------|---------------|---------|
| GET | `/` | — | hub.html or redirect to /login |
| GET | `/login` | — | login.html |
| POST | `/login` | `{name, balance?}` | `{ok, redirect}` |
| GET | `/game/<name>` | — | templates/games/<name>.html (GAMES list) |
| GET | `/job/<name>` | — | templates/games/<name>.html (JOBS list, earn money) |
| GET | `/api/state` | — | `{player_name, balance, debt, stats}` |
| POST | `/api/state` | `{balance?, debt?, stats?}` | `{ok, balance, debt}` |
| GET | `/api/hint/<game>` | — | `{term, explanation}` |
| POST | `/api/save` | — | `{ok, filename}` |
| GET | `/api/load/<name>` | — | `{ok, state}` or `{error}` |
| GET | `/api/saves` | — | `[{name, balance, saved_at}]` |

---

## JavaScript Contract — game.js

Every mini-game gets these globals from `game.js` (included via base.html):

```javascript
// Read current state (async, hits /api/state)
const state = await GameAPI.getState();
// state = { player_name, balance, debt, stats }

// Exit a mini-game — updates session and goes back to hub
await GameAPI.exit(newBalance);
// Optionally pass stat updates:
await GameAPI.exit(newBalance, { bribes_used: state.stats.bribes_used + 1 });

// Patch state mid-game without exiting (e.g. update debt)
await GameAPI.patch({ debt: newDebt });

// Get a hint for this game (uses current page URL to infer game name)
const hint = await GameAPI.getHint();
// hint = { term: "Kamat", explanation: "Az adósság éves költsége..." }

// EventBus — for communication within a single page
EventBus.on('balance:update', ({ balance }) => { ... });
EventBus.emit('balance:update', { balance: 500 });
// Built-in events: 'balance:update', 'debt:update', 'npc:speak', 'game:over'
```

---

## GAMES vs JOBS

`app.py` maintains two separate lists:
- `GAMES` — `/game/<name>` routes, player spends money, debt interest applies
- `JOBS` — `/job/<name>` routes, player earns money, no debt interest

## How to Add a Mini-Game

1. Copy `templates/games/_template.html` → `templates/games/yourname.html`
2. Add the name to `GAMES` list in `app.py`:
   ```python
   GAMES = ["casino", "horse_race", "stock_market", "slots", "chess", "yourname"]
   ```
3. Add a building button in `hub.html` (follow the existing pattern).
4. Add hints in `data/hints.json` under the key `"yourname"`.
5. Done. Don't touch anyone else's files.

## How to Add a Job

1. Copy `templates/games/_template.html` → `templates/games/yourjob.html`
2. Add the name to `JOBS` list in `app.py`:
   ```python
   JOBS = ["cashier", "warehouse", "taxi", "cook", "yourjob"]
   ```
3. Add a job card in `hub.html` (follow the `.job-card` pattern).
4. Done. No hints needed, no debt interest applied.

### Mini-game template skeleton

```html
{% extends "base.html" %}
{% block title %}Játék neve{% endblock %}
{% block content %}
<div id="game-container">
  <div id="npc-hint"></div>
  <!-- your game here -->
  <button onclick="exitGame()">Kilépés</button>
</div>
{% endblock %}
{% block scripts %}
<script>
let state;

async function init() {
  state = await GameAPI.getState();
  const hint = await GameAPI.getHint();
  document.getElementById('npc-hint').textContent =
    `💡 ${hint.term}: ${hint.explanation}`;
  // start your game
}

async function exitGame() {
  const newBalance = calculateFinalBalance(); // your logic
  await GameAPI.exit(newBalance);
}

init();
</script>
{% endblock %}
```

---

## Debt Rules

- If `balance < 0` after any game, Flask auto-sets `debt += abs(balance)`, `balance = 0`
- The hub shows a "Fizess vissza" (Pay back) button when `debt > 0`
- Debt accrues 10% interest every time the player enters a new game (applied server-side in `/game/<name>`)
- Loan shark NPC appears (hub overlay) when `debt > 5000`

Apply debt interest in `app.py` before rendering any game page:
```python
if session.get('debt', 0) > 0:
    session['debt'] = int(session['debt'] * 1.10)
```

---

## NPC Hint System

`data/hints.json` structure:
```json
{
  "horse_race": [
    { "term": "Kockázat", "explanation": "Annak valószínűsége, hogy elveszíted a pénzed. Magas." },
    { "term": "Várható érték", "explanation": "Átlagos nyereményed hosszú távon. Negatív." }
  ],
  "casino": [ ... ],
  "global": [ ... ]
}
```

`GET /api/hint/<game>` picks randomly from `hints[game]` + `hints["global"]`.

---

## Coding Rules

- **No external JS libraries** — vanilla JS only, no jQuery, no React
- **No inline styles** — use CSS classes from style.css or add new ones
- **CSS variables only** — never hardcode colors, use `var(--gold)`, `var(--dark)` etc.
- **Flask session only** for state — never write to saves/ during a game
- **Guard every route** — redirect to `/login` if `player_name` not in session
- **No global variable conflicts** — wrap game logic in an IIFE or module pattern
- **Keep game files self-contained** — one HTML file per game, logic inside `{% block scripts %}`

---

## CSS Variables (defined in style.css)

```css
--gold:        #C9A84C
--gold-light:  #F0D080
--dark:        #1A1A2E
--dark-mid:    #2A2A4E
--red:         #8B1A1A
--green:       #2E7D32
--green-light: #4CAF50
--cream:       #F5F0E8
--shadow:      rgba(0,0,0,0.4)
--font-display: 'Playfair Display', Georgia, serif
--font-body:    'Crimson Text', Georgia, serif
--font-mono:    'Courier New', monospace
```

---

## Running Locally

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

---

## Git Workflow (team)

- `main` branch = working hub + shared files only
- Each person works on a feature branch: `feature/horse-race`, `feature/casino`, etc.
- Only touch your own `templates/games/<yourname>.html`
- Shared files (`app.py`, `game.js`, `style.css`, `hub.html`) → coordinate before editing
- PRs require at least one teammate to test locally before merge
