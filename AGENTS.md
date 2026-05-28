# 🤖 Agent Guide — Pénz Plaza

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
├── AGENTS.md              ← you are here
├── app.py                 ← Flask server, all routes
├── requirements.txt       ← Python dependencies
├── data/
│   └── hints.json         ← NPC financial term hints (term + explanation)
├── saves/                 ← player JSON save files (auto-created)
├── static/
│   ├── css/
│   │   └── style.css      ← shared styles, CSS variables, fonts
│   ├── js/
│   │   ├── game.js        ← shared JS: GameAPI, EventBus, utilities
│   │   └── vendor/
│   │       └── chess.min.js  ← vendored chess.js (full legal chess rules)
│   └── assets/            ← images, sprites (PNG, all with transparent bg)
├── templates/
│   ├── base.html           ← base Jinja2 template (head, nav, scripts)
│   ├── hub.html            ← main town map, clickable buildings
│   ├── login.html          ← name entry / new game / load game
│   └── games/              ← all game templates (GAMES + JOBS)
│       ├── _template.html  ← copy this to add a new mini-game / job
│       ├── casino.html      ← lobby + slots / blackjack / corrupt dice
│       ├── horse_race.html  ← bet on 4 horses, animated SVG runners + jockey
│       ├── stock_market.html← 6-stock ticker, liquidity/slippage, upgrades, OIL→taxi link
│       ├── slots.html       ← lobby + quiz / bingo / wheel / scratch subgames
│       ├── chess.html       ← chess with chess.js rules; easy/medium/hard/ultra (Stockfish CDN)
│       ├── pachinko.html    ← pachinko ball-drop game
│       ├── scam.html        ← Szélhámosok Utcája: 7 scam-themed subgames lobby
│       ├── cashier.html     ← job: conveyor-belt item scanning, 90s shift
│       ├── warehouse.html   ← job: box sorting by category/shelf, number-key shortcuts
│       ├── taxi.html        ← job: canvas WASD road game, fuel gauge, OIL price link, autopilot
│       └── cook.html        ← job: recipe sequence game, number-key ingredient shortcuts
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
        "games_played":    int,
        "bribes_used":     int,
        "times_employed":  int,
        "biggest_win":     int,
        "biggest_loss":    int,
        "oil_price":       int,   # synced from stock market OIL stock → read by taxi
        "autopilot_unlocked": bool,  # one-time 8000 Ft taxi autopilot purchase
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

// Patch state mid-game without exiting (e.g. update balance after a round)
S = await GameAPI.patch({ balance: S.balance + delta });

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
```python
GAMES = ["casino", "horse_race", "stock_market", "slots", "chess", "pachinko", "scam"]
JOBS  = ["cashier", "warehouse", "taxi", "cook"]
```

- `GAMES` — `/game/<name>` routes, player spends money, **debt interest applies on entry**
- `JOBS` — `/job/<name>` routes, player earns money, no debt interest

## How to Add a Mini-Game

1. Copy `templates/games/_template.html` → `templates/games/yourname.html`
2. Add the name to `GAMES` list in `app.py`.
3. Add a building button in `hub.html` (follow the existing `.map-hotspot` pattern).
4. Add hints in `data/hints.json` under the key `"yourname"`.
5. Done. Don't touch anyone else's files.

## How to Add a Job

1. Copy `templates/games/_template.html` → `templates/games/yourjob.html`
2. Add the name to `JOBS` list in `app.py`.
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

## Multi-Screen Lobby Games

Several games are **multi-screen apps** rendered as a single HTML file:

### casino.html
- Lobby with 3 hotspots over `casino_lobby.png` → Slots, Blackjack, Corrupt Dice
- Public API: `window.CAS` — `CAS.sl`, `CAS.bj`, `CAS.dc`, `CAS.enter(game)`, `CAS.showLobby()`, `CAS.exitCasino()`
- Blackjack: uses separate `roundBet` (not `bet`) so double-down never leaks into next hand

### slots.html
- Lobby with 4 buttons → Quiz, Bingo, Wheel, Scratch subgames
- Public API: `window.SL`

### scam.html — Szélhámosok Utcája
- Dark street lobby with 7 clickable game cards:
  1. 🏝️ **Adóparadicsom** (offshore) — location picker, transaction animation, NAV audit risk
  2. 💼 **Kamu Befektetési Tanácsadó** — advise 5 clients, earn fees, 90% chance of complaint
  3. 👮 **Szerencsejáték Felügyelő** — inspect 5 casinos, guess violation level
  4. 🏥 **Biztosítási Csaló** — file insurance claim, usually rejected with absurd reasons
  5. 🧺 **Pénzmosó Szalon** — 5-step laundering process, random police catches
  6. 🏠 **Ingatlan Spekuláns** — buy property, random market events, almost always bad
  7. 🔺 **Piramis Játék** — auto-runs rounds recruiting members, always collapses
- Public API: `window.SC` — `SC.off`, `SC.adv`, `SC.ins`, `SC.insur`, `SC.laun`, `SC.real`, `SC.pyr`, `SC.enter(game)`, `SC.showLobby()`, `SC.exitScam()`
- Lobby stats panel tracks totalGames, totalWins, totalLosses, totalBalance across all 7 subgames
- All subgames use `applyDelta(delta)` which calls `GameAPI.patch` and `refreshBalances()`
- `hints.json` key `"scam"` has 10 scam-themed hints (biztosítási csalás, korrupció, etc.)

---

## Cross-Game State: OIL Price

- `stock_market.html` has an OIL stock (`id:'OIL'`, p:1000). When OIL price moves >4%, it writes `stats.oil_price` via `GameAPI.patch`.
- `taxi.html` reads `S.stats.oil_price` on init and on taxi game start to set `oilPrice`. Fuel tank price = `Math.round(120 * oilPrice / 1000)`. This creates a real gameplay link between the two games.

---

## Chess Notes

- `chess.html` loads `static/js/vendor/chess.min.js` (vendored chess.js) for full legal move generation: castling, en passant, promotion, checkmate, stalemate, threefold repetition, 50-move rule, insufficient material.
- Difficulty: easy (random), medium (minimax depth-2), hard (minimax depth-3), **ultra** (Stockfish.js from CDN as Web Worker, local minimax fallback if load fails).
- chess.js is justified as it provides correct rule handling that would be very error-prone to reimplement manually.

---

## Taxi Job Notes

- Canvas-based WASD road game; logical canvas W=700, H=420, rendered at 1.5× scale.
- Roads: H1 (y 65-115), H2 (y 285-335), V1 (x 60-110), V2 (x 315-365), V3 (x 565-615). `onRoad(x,y)` enforces road collision.
- Autopilot: one-time 8000 Ft purchase, stored in `stats.autopilot_unlocked`. BFS over 6 named intersections.
- Fuel: starts at 100, consumed at `moved * 0.007` px/frame. Gas station at ~(460, 90), auto-refuels when near. Tank cost = `Math.round(120 * oilPrice / 1000)`.
- Fare: flat 280 Ft per delivery. The "app takes 75%" is cosmetic NPC joke only; player receives full 280 Ft.
- Speed: `const SPEED = 1.2` px/frame.

---

## Debt Rules

- If `balance < 0` after any game, Flask auto-sets `debt += abs(balance)`, `balance = 0`
- The hub shows a "Fizess vissza" (Pay back) button when `debt > 0`
- Debt accrues 10% interest every time the player enters a new game (applied server-side in `/game/<name>`)
- Loan shark NPC appears (hub overlay) when `debt > 5000`

---

## NPC Hint System

`data/hints.json` structure:
```json
{
  "horse_race": [ { "term": "...", "explanation": "..." } ],
  "casino": [ ... ],
  "scam":   [ ... ],
  "global": [ ... ]
}
```

Keys present: `global`, `horse_race`, `casino`, `stock_market`, `slots`, `chess`, `cashier`, `quiz`, `bingo`, `wheel`, `pachinko`, `scam`, `taxi` (from subagent).

`GET /api/hint/<game>` picks randomly from `hints[game]` + `hints["global"]`.

---

## Coding Rules

- **External JS libraries are allowed when justified** — prefer small, focused libraries and document why they are used (see chess.js above)
- **No inline styles** — use CSS classes from style.css or add new ones
- **CSS variables only** — never hardcode colors, use `var(--gold)`, `var(--dark)` etc.
- **Flask session only** for state — never write to saves/ during a game
- **Guard every route** — redirect to `/login` if `player_name` not in session
- **No global variable conflicts** — wrap game logic in an IIFE or module pattern
- **Keep game files self-contained** — one HTML file per game, logic inside `{% block scripts %}`
- **`[hidden] { display: none !important; }`** — always add this rule in game CSS to prevent button state leaks after `setAttribute('hidden','')`

---

## CSS Variables (defined in style.css)

```css
--gold:        #C9A84C
--gold-light:  #F0D080
--gold-dim:    rgba(201,168,76,0.35)
--dark:        #1A1A2E
--dark-mid:    #2A2A4E
--dark-light:  #3A3A5E
--red:         #8B1A1A
--red-light:   #ffcdd2
--green:       #2E7D32
--green-light: #4CAF50
--cream:       #F5F0E8
--cream-dark:  #c8b99a
--shadow:      rgba(0,0,0,0.4)
--shadow-gold: rgba(201,168,76,0.25)
--font-display: 'Playfair Display', Georgia, serif
--font-body:    'Crimson Text', Georgia, serif
--font-mono:    'Courier New', monospace
--radius:       8px
--transition:   0.2s ease
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
