"""
MONK-OS V2 — Local SQLite Database Layer
All data stays on-device: ~/monk_os_data.db
"""

import sqlite3
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path.home() / "monk_os_data.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables on first run, migrate existing ones."""
    conn = get_connection()
    c    = conn.cursor()

    # Settings / configuration
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Monthly finances snapshots (extended with investment columns)
    c.execute("""
        CREATE TABLE IF NOT EXISTS finances (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            month_key           TEXT NOT NULL UNIQUE,
            date                TEXT NOT NULL,
            income              REAL DEFAULT 0,
            rent                REAL DEFAULT 0,
            food                REAL DEFAULT 0,
            transport           REAL DEFAULT 0,
            misc                REAL DEFAULT 0,
            savings             REAL DEFAULT 0,
            investments_etf     REAL DEFAULT 0,
            investments_crypto  REAL DEFAULT 0,
            investments_other   REAL DEFAULT 0,
            note                TEXT
        )
    """)

    # V2 — Dynamic multi-ETF portfolio rows
    c.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_v2 (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            shares      REAL DEFAULT 0,
            price       REAL DEFAULT 0,
            target_pct  REAL DEFAULT 0
        )
    """)

    # Sentinel discipline journal
    c.execute("""
        CREATE TABLE IF NOT EXISTS sentinel_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            is_calm     TEXT,
            is_planned  TEXT,
            action      TEXT,
            verdict     TEXT,
            greed_index INTEGER DEFAULT 50
        )
    """)

    # Migrate old finances table if month_key column missing
    try:
        c.execute("ALTER TABLE finances ADD COLUMN month_key TEXT")
        conn.commit()
        # backfill month_key for existing rows
        c.execute("UPDATE finances SET month_key = substr(date,1,7) WHERE month_key IS NULL OR month_key = ''")
        conn.commit()
    except Exception:
        pass  # column already exists

    # Migrate: add investment columns if missing
    for col in ["investments_etf REAL DEFAULT 0",
                "investments_crypto REAL DEFAULT 0",
                "investments_other REAL DEFAULT 0"]:
        try:
            c.execute(f"ALTER TABLE finances ADD COLUMN {col}")
        except Exception:
            pass

    # Migrate sentinel_log: add greed_index if missing
    try:
        c.execute("ALTER TABLE sentinel_log ADD COLUMN greed_index INTEGER DEFAULT 50")
    except Exception:
        pass

    conn.commit()
    conn.close()
    _seed_defaults()


def _seed_defaults():
    conn = get_connection()
    c    = conn.cursor()
    defaults = {
        "monk_mode_end_date": "2026-04-09",
        "savings_goal":       "2000",
        "monthly_budget":     "1250",
        "current_savings":    "0",
        "preferred_currency": "EUR",
        "preferred_timezone": "Europe/Brussels",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()


# ── SETTINGS ────────────────────────────────────────────────────────────────

def get_setting(key: str, default=None):
    conn = get_connection()
    row  = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


# ── FINANCES ─────────────────────────────────────────────────────────────────

def upsert_finance_entry(month_key: str, income, rent, food, transport, misc,
                         investments_etf=0, investments_crypto=0, investments_other=0,
                         note=""):
    """Insert or update a monthly finance record. month_key = 'YYYY-MM'.
    Uses INSERT OR IGNORE + UPDATE to work with existing DBs without UNIQUE constraint."""
    total_invest = investments_etf + investments_crypto + investments_other
    savings      = income - rent - food - transport - misc - total_invest
    conn         = get_connection()
    # First ensure the row exists (ignored if month_key already in DB)
    conn.execute("""
        INSERT OR IGNORE INTO finances
            (month_key, date, income, rent, food, transport, misc, savings,
             investments_etf, investments_crypto, investments_other, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (month_key, f"{month_key}-01", income, rent, food, transport, misc,
          savings, investments_etf, investments_crypto, investments_other, note))
    # Then update all fields (covers both insert and update cases)
    conn.execute("""
        UPDATE finances SET
            date=?, income=?, rent=?, food=?, transport=?, misc=?, savings=?,
            investments_etf=?, investments_crypto=?, investments_other=?, note=?
        WHERE month_key=?
    """, (f"{month_key}-01", income, rent, food, transport, misc, savings,
          investments_etf, investments_crypto, investments_other, note, month_key))
    conn.commit()
    conn.close()
    set_setting("current_savings", savings)
    return savings


def delete_finance_entry(month_key: str):
    """Delete a monthly finance record by month_key."""
    conn = get_connection()
    conn.execute("DELETE FROM finances WHERE month_key=?", (month_key,))
    conn.commit()
    conn.close()


def get_finance_for_month(month_key: str):
    """Return a single row for a given month_key ('YYYY-MM'), or None."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT * FROM finances WHERE month_key=?", (month_key,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_finances():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM finances ORDER BY month_key DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_finance():
    conn = get_connection()
    row  = conn.execute("SELECT * FROM finances ORDER BY month_key DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


# ── PORTFOLIO V2 ──────────────────────────────────────────────────────────────

def save_portfolio_v2(rows: list[dict]):
    """
    rows = [{"ticker": "VWCE.DE", "shares": 5.0, "price": 120.5, "target_pct": 80.0}, ...]
    Replaces today's snapshot.
    """
    conn    = get_connection()
    today   = date.today().isoformat()
    # Delete today's entries first
    conn.execute("DELETE FROM portfolio_v2 WHERE date=?", (today,))
    for r in rows:
        conn.execute("""
            INSERT INTO portfolio_v2 (date, ticker, shares, price, target_pct)
            VALUES (?, ?, ?, ?, ?)
        """, (today, r["ticker"], r.get("shares", 0), r.get("price", 0), r.get("target_pct", 0)))
    conn.commit()
    conn.close()


def get_latest_portfolio_v2() -> list[dict]:
    """Returns the most recent portfolio snapshot rows."""
    conn  = get_connection()
    today = conn.execute("SELECT MAX(date) FROM portfolio_v2").fetchone()[0]
    if not today:
        conn.close()
        return []
    rows = conn.execute(
        "SELECT * FROM portfolio_v2 WHERE date=? ORDER BY id", (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_latest_portfolio():
    """Backward-compatible: returns first row as a dict (for Fortress One)."""
    rows = get_latest_portfolio_v2()
    if not rows:
        return None
    # Aggregate value for backward compat
    total_value = sum(r["shares"] * r["price"] for r in rows)
    return {"total_value": total_value, "rows": rows}


# ── SENTINEL ─────────────────────────────────────────────────────────────────

def log_sentinel(is_calm: str, is_planned: str, action: str, verdict: str,
                 greed_index: int = 50):
    conn = get_connection()
    conn.execute("""
        INSERT INTO sentinel_log (timestamp, is_calm, is_planned, action, verdict, greed_index)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), is_calm, is_planned, action, verdict, greed_index))
    conn.commit()
    conn.close()


def get_sentinel_logs(limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sentinel_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
