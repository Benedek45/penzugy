/**
 * game.js — [PROJECT_NAME] shared utilities
 *
 * Globals exposed:
 *   GameAPI  — async state/save/hint methods
 *   EventBus — pub/sub for in-page events
 *   Toast    — notification helper
 *   fmt      — currency formatter
 */

// ── EventBus ──────────────────────────────────────────────────────────────
const EventBus = (() => {
  const listeners = {};
  return {
    on(event, cb) {
      if (!listeners[event]) listeners[event] = [];
      listeners[event].push(cb);
    },
    off(event, cb) {
      if (!listeners[event]) return;
      listeners[event] = listeners[event].filter(fn => fn !== cb);
    },
    emit(event, data = {}) {
      (listeners[event] || []).forEach(cb => cb(data));
    },
  };
})();

// Built-in events:
//   'balance:update'  { balance, delta }
//   'debt:update'     { debt }
//   'npc:speak'       { term, explanation }
//   'game:over'       { won, delta }
//   'state:loaded'    { state }

// ── Currency formatter ─────────────────────────────────────────────────────
function fmt(amount) {
  const abs = Math.abs(Math.round(amount));
  const str = abs.toLocaleString('hu-HU');
  return (amount < 0 ? '-' : '') + str + ' Ft';
}

// ── API layer ──────────────────────────────────────────────────────────────
const GameAPI = (() => {
  let _state = null;

  async function _fetch(url, options = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  return {
    /**
     * Get full current state from server session.
     * Caches within the same page load.
     */
    async getState(forceRefresh = false) {
      if (_state && !forceRefresh) return _state;
      _state = await _fetch('/api/state');
      EventBus.emit('state:loaded', { state: _state });
      return _state;
    },

    /**
     * Patch state on the server (balance, debt, or stats).
     * @param {Object} patch - Fields to update
     */
    async patch(patch) {
      const prev = _state ? { ..._state } : null;
      _state = await _fetch('/api/state', {
        method: 'POST',
        body: JSON.stringify(patch),
      });
      if (prev && _state.balance !== prev.balance) {
        EventBus.emit('balance:update', {
          balance: _state.balance,
          delta: _state.balance - prev.balance,
        });
      }
      if (prev && _state.debt !== prev.debt) {
        EventBus.emit('debt:update', { debt: _state.debt });
      }
      return _state;
    },

    /**
     * Exit the current mini-game: update balance + redirect to hub.
     * @param {number} newBalance
     * @param {Object} statsUpdate - Optional stats fields to update
     */
    async exit(newBalance, statsUpdate = {}) {
      const patch = { balance: newBalance };
      if (Object.keys(statsUpdate).length) patch.stats = statsUpdate;
      await this.patch(patch);
      window.location.href = '/';
    },

    /**
     * Get a random NPC hint for the current game.
     * Infers game name from the URL path.
     */
    async getHint(gameName = null) {
      if (!gameName) {
        const parts = window.location.pathname.split('/');
        gameName = parts[parts.length - 1] || 'global';
      }
      return _fetch(`/api/hint/${gameName}`);
    },

    /** Save current session to file. */
    async save() {
      const result = await _fetch('/api/save', { method: 'POST' });
      Toast.show('💾 Játék mentve!', 'win');
      return result;
    },

    /** List all save files. */
    async listSaves() {
      return _fetch('/api/saves');
    },
  };
})();

// ── Toast notifications ───────────────────────────────────────────────────
const Toast = (() => {
  let container;

  function ensure() {
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
  }

  return {
    show(message, type = '', duration = 3000) {
      ensure();
      const el = document.createElement('div');
      el.className = `toast ${type}`;
      el.textContent = message;
      container.appendChild(el);
      setTimeout(() => {
        el.style.animation = 'toast-out 0.3s ease forwards';
        setTimeout(() => el.remove(), 300);
      }, duration);
    },
  };
})();

// ── Navbar updater ─────────────────────────────────────────────────────────
EventBus.on('balance:update', ({ balance }) => {
  const el = document.getElementById('nav-balance');
  if (el) {
    el.textContent = fmt(balance);
    el.className = balance < 0 ? 'negative' : '';
  }
});

EventBus.on('debt:update', ({ debt }) => {
  const el = document.getElementById('nav-debt');
  if (el) {
    el.textContent = debt > 0 ? `Adósság: ${fmt(debt)}` : '';
    el.style.display = debt > 0 ? 'inline' : 'none';
  }
});

// ── Auto-load NPC hint if element exists ───────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const hintEl = document.getElementById('npc-hint');
  if (hintEl) {
    try {
      const hint = await GameAPI.getHint();
      hintEl.innerHTML = `<strong>${hint.term}:</strong> ${hint.explanation}`;
      EventBus.emit('npc:speak', hint);
    } catch (e) {
      console.warn('Hint load failed', e);
    }
  }

  // Refresh navbar balance
  try {
    const state = await GameAPI.getState();
    const navBal = document.getElementById('nav-balance');
    const navDebt = document.getElementById('nav-debt');
    if (navBal) navBal.textContent = fmt(state.balance);
    if (navDebt) {
      navDebt.textContent = state.debt > 0 ? `Adósság: ${fmt(state.debt)}` : '';
      navDebt.style.display = state.debt > 0 ? 'inline' : 'none';
    }
  } catch (e) {}
});
