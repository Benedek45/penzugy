import json
import os
import random
from datetime import datetime
from flask import Flask, render_template, session, redirect, request, jsonify

app = Flask(__name__)
app.secret_key = "[PROJECT_NAME]_secret_2026"

SAVES_DIR = os.path.join(os.path.dirname(__file__), "saves")
HINTS_FILE = os.path.join(os.path.dirname(__file__), "data", "hints.json")
STARTING_BALANCE = 10_000

os.makedirs(SAVES_DIR, exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────

def load_hints():
    with open(HINTS_FILE, encoding="utf-8") as f:
        return json.load(f)

def get_save_path(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in ("_", "-"))
    return os.path.join(SAVES_DIR, f"{safe}.json")

def session_to_dict() -> dict:
    return {
        "player_name": session.get("player_name"),
        "balance":     session.get("balance", STARTING_BALANCE),
        "debt":        session.get("debt", 0),
        "stats":       session.get("stats", default_stats()),
    }

def default_stats() -> dict:
    return {
        "games_played":   0,
        "bribes_used":    0,
        "times_employed": 0,
        "biggest_win":    0,
        "biggest_loss":   0,
    }

def apply_debt_interest():
    """Apply 10% interest on debt when entering any game."""
    debt = session.get("debt", 0)
    if debt > 0:
        session["debt"] = int(debt * 1.10)

def resolve_negative_balance():
    """If balance went negative, roll it into debt."""
    bal = session.get("balance", 0)
    if bal < 0:
        session["debt"] = session.get("debt", 0) + abs(bal)
        session["balance"] = 0

# ── auth guard ─────────────────────────────────────────────────────────────

def require_login():
    if "player_name" not in session:
        return redirect("/login")
    return None

# ── routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def hub():
    guard = require_login()
    if guard:
        return guard
    return render_template("hub.html", state=session_to_dict())


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Adj meg egy nevet!"}), 400

    save_path = get_save_path(name)
    if os.path.exists(save_path):
        with open(save_path, encoding="utf-8") as f:
            saved = json.load(f)
        session.update(saved)
    else:
        session["player_name"] = name
        session["balance"]     = STARTING_BALANCE
        session["debt"]        = 0
        session["stats"]       = default_stats()

    return jsonify({"ok": True, "redirect": "/"})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ── game routes ────────────────────────────────────────────────────────────

GAMES = ["casino", "horse_race", "stock_market", "slots", "chess"]
JOBS  = ["cashier", "warehouse", "taxi", "cook"]

@app.route("/game/<name>")
def game(name):
    guard = require_login()
    if guard:
        return guard
    if name not in GAMES:
        return redirect("/")
    apply_debt_interest()
    stats = session.get("stats", default_stats())
    stats["games_played"] = stats.get("games_played", 0) + 1
    session["stats"] = stats
    return render_template(f"games/{name}.html", state=session_to_dict())


@app.route("/job/<name>")
def job(name):
    guard = require_login()
    if guard:
        return guard
    if name not in JOBS:
        return redirect("/")
    stats = session.get("stats", default_stats())
    stats["times_employed"] = stats.get("times_employed", 0) + 1
    session["stats"] = stats
    return render_template(f"games/{name}.html", state=session_to_dict())


# ── api ────────────────────────────────────────────────────────────────────

@app.route("/api/state", methods=["GET"])
def api_state_get():
    guard = require_login()
    if guard:
        return jsonify({"error": "not logged in"}), 401
    return jsonify(session_to_dict())


@app.route("/api/state", methods=["POST"])
def api_state_post():
    guard = require_login()
    if guard:
        return jsonify({"error": "not logged in"}), 401

    data = request.get_json(silent=True) or {}

    if "balance" in data:
        old_bal = session.get("balance", 0)
        new_bal = int(data["balance"])
        delta = new_bal - old_bal
        stats = session.get("stats", default_stats())
        if delta > 0:
            stats["biggest_win"] = max(stats.get("biggest_win", 0), delta)
        elif delta < 0:
            stats["biggest_loss"] = max(stats.get("biggest_loss", 0), abs(delta))
        session["stats"] = stats
        session["balance"] = new_bal

    if "debt" in data:
        session["debt"] = int(data["debt"])

    if "stats" in data:
        current = session.get("stats", default_stats())
        current.update(data["stats"])
        session["stats"] = current

    resolve_negative_balance()
    return jsonify(session_to_dict())


@app.route("/api/hint/<game_name>")
def api_hint(game_name):
    hints = load_hints()
    pool = hints.get(game_name, []) + hints.get("global", [])
    if not pool:
        pool = [{"term": "Kamat", "explanation": "Pénz ára az időben."}]
    return jsonify(random.choice(pool))


@app.route("/api/save", methods=["POST"])
def api_save():
    guard = require_login()
    if guard:
        return jsonify({"error": "not logged in"}), 401
    state = session_to_dict()
    state["saved_at"] = datetime.now().isoformat()
    path = get_save_path(state["player_name"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True, "filename": os.path.basename(path)})


@app.route("/api/load/<name>")
def api_load(name):
    path = get_save_path(name)
    if not os.path.exists(path):
        return jsonify({"error": "Nincs mentett játék ezzel a névvel."}), 404
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    return jsonify({"ok": True, "state": saved})


@app.route("/api/saves")
def api_saves():
    saves = []
    for fname in os.listdir(SAVES_DIR):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(SAVES_DIR, fname), encoding="utf-8") as f:
                    d = json.load(f)
                saves.append({
                    "name":     d.get("player_name", fname),
                    "balance":  d.get("balance", 0),
                    "debt":     d.get("debt", 0),
                    "saved_at": d.get("saved_at", ""),
                })
            except Exception:
                pass
    return jsonify(saves)


# ── run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)
