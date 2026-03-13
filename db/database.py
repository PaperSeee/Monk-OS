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

    # MT — Prop firm challenges
    c.execute("""
        CREATE TABLE IF NOT EXISTS prop_challenges (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at   TEXT NOT NULL,
            account_size REAL DEFAULT 0,
            price        REAL DEFAULT 0,
            status       TEXT DEFAULT 'En cours',
            is_funded    INTEGER DEFAULT 0,
            payouts      REAL DEFAULT 0
        )
    """)

    # CT — Business tests sandbox
    c.execute("""
        CREATE TABLE IF NOT EXISTS business_tests (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at       TEXT NOT NULL,
            name             TEXT NOT NULL,
            description      TEXT DEFAULT '',
            status           TEXT DEFAULT 'To Do',
            allocated_budget REAL DEFAULT 0,
            cash_burn        REAL DEFAULT 0
        )
    """)

    # MT — Prop payouts history (tracks each payout individually)
    c.execute("""
        CREATE TABLE IF NOT EXISTS prop_payouts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id   INTEGER NOT NULL,
            amount         REAL DEFAULT 0,
            created_at     TEXT NOT NULL,
            note           TEXT DEFAULT '',
            FOREIGN KEY (challenge_id) REFERENCES prop_challenges(id)
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

    # Migrate prop_challenges: add is_funded column if missing
    try:
        c.execute("ALTER TABLE prop_challenges ADD COLUMN is_funded INTEGER DEFAULT 0")
        conn.commit()
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
        "lt_capital":         "0",
        "preferred_currency": "EUR",
        "preferred_timezone": "Europe/Brussels",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Backward-compat: if LT capital was never set, seed it from current_savings
    row_lt = c.execute("SELECT value FROM settings WHERE key='lt_capital'").fetchone()
    if not row_lt or row_lt["value"] in (None, ""):
        row_s = c.execute("SELECT value FROM settings WHERE key='current_savings'").fetchone()
        seed_val = row_s["value"] if row_s and row_s["value"] not in (None, "") else "0"
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("lt_capital", seed_val))

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


def get_lt_capital() -> float:
    raw = get_setting("lt_capital", None)
    if raw is None:
        raw = get_setting("current_savings", "0")
        set_setting("lt_capital", raw)
    try:
        return float(raw)
    except Exception:
        return 0.0


def set_lt_capital(amount: float):
    set_setting("lt_capital", amount)
    set_setting("current_savings", amount)


def adjust_lt_capital(delta: float) -> float:
    new_value = get_lt_capital() + float(delta)
    set_lt_capital(new_value)
    return new_value


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


# ── PROP CHALLENGES (MT) ─────────────────────────────────────────────────────

def create_prop_challenge(account_size: float, price: float, status: str = "En cours"):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO prop_challenges (created_at, account_size, price, status, payouts)
        VALUES (?, ?, ?, ?, 0)
        """,
        (datetime.now().isoformat(), account_size, price, status),
    )
    conn.commit()
    conn.close()
    adjust_lt_capital(-float(price))


def add_prop_payout(challenge_id: int, amount: float, note: str = ""):
    """Add a payout to a challenge and credit LT capital."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO prop_payouts (challenge_id, amount, created_at, note)
        VALUES (?, ?, ?, ?)
        """,
        (challenge_id, float(amount), datetime.now().isoformat(), note),
    )
    conn.commit()
    conn.close()
    adjust_lt_capital(float(amount))


def get_prop_payouts(challenge_id: int):
    """Get all payouts for a challenge."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM prop_payouts WHERE challenge_id = ? ORDER BY created_at DESC",
        (challenge_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_prop_challenge_status(challenge_id: int, status: str):
    conn = get_connection()
    conn.execute("UPDATE prop_challenges SET status = ? WHERE id = ?", (status, challenge_id))
    conn.commit()
    conn.close()


def set_challenge_funded(challenge_id: int, is_funded: bool):
    conn = get_connection()
    conn.execute("UPDATE prop_challenges SET is_funded = ? WHERE id = ?", (1 if is_funded else 0, challenge_id))
    conn.commit()
    conn.close()


def delete_prop_challenge(challenge_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT price FROM prop_challenges WHERE id = ?", (challenge_id,))
    row = c.fetchone()
    if row:
        refund = float(row[0])
        c.execute("DELETE FROM prop_challenges WHERE id = ?", (challenge_id,))
        conn.commit()
        conn.close()
        adjust_lt_capital(refund)
        return refund
    conn.close()
    return 0.0


def delete_prop_payout(challenge_id: int, payout_id: int, amount: float):
    """Remove a payout from history and refund to LT capital."""
    conn = get_connection()
    conn.execute("DELETE FROM prop_payouts WHERE id = ?", (payout_id,))
    conn.commit()
    conn.close()
    adjust_lt_capital(-float(amount))


def get_prop_challenges():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM prop_challenges ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_payouts(challenge_id: int):
    """Get total payout amount for a challenge."""
    conn = get_connection()
    row = conn.execute(
        "SELECT SUM(amount) as total FROM prop_payouts WHERE challenge_id = ?",
        (challenge_id,),
    ).fetchone()
    conn.close()
    return float(row["total"] or 0)


def get_prop_challenges_by_status(status: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM prop_challenges WHERE status = ? ORDER BY created_at DESC", (status,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── BUSINESS TESTS (CT) ──────────────────────────────────────────────────────

def create_business_test(name: str, description: str, status: str = "To Do",
                         allocated_budget: float = 0.0, deduct_from_lt: bool = False):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO business_tests (created_at, name, description, status, allocated_budget, cash_burn)
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (datetime.now().isoformat(), name, description, status, float(allocated_budget)),
    )
    conn.commit()
    conn.close()
    if deduct_from_lt and allocated_budget > 0:
        adjust_lt_capital(-float(allocated_budget))


def update_business_test_status(test_id: int, status: str):
    conn = get_connection()
    conn.execute("UPDATE business_tests SET status = ? WHERE id = ?", (status, test_id))
    conn.commit()
    conn.close()


def add_business_cash_burn(test_id: int, amount: float, deduct_from_lt: bool = False):
    conn = get_connection()
    conn.execute("UPDATE business_tests SET cash_burn = cash_burn + ? WHERE id = ?", (float(amount), test_id))
    conn.commit()
    conn.close()
    if deduct_from_lt and amount > 0:
        adjust_lt_capital(-float(amount))


def get_business_tests():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM business_tests ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
