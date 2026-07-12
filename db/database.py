"""
MONK-OS V2 — Local SQLite Database Layer
All data stays on-device: <project_root>/monk_os_data.db
"""

import sqlite3
from pathlib import Path
from datetime import datetime, date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "monk_os_data.db"


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

    # Risk Investments — Crypto, speculative stocks, etc.
    c.execute("""
        CREATE TABLE IF NOT EXISTS risk_investments (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at     TEXT NOT NULL,
            name           TEXT NOT NULL,
            asset_type     TEXT DEFAULT 'Crypto',
            quantity       REAL DEFAULT 0,
            entry_price    REAL DEFAULT 0,
            current_price  REAL DEFAULT 0,
            note           TEXT DEFAULT ''
        )
    """)

    # CT — Payout transfers back to LT capital
    c.execute("""
        CREATE TABLE IF NOT EXISTS ct_payouts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at   TEXT NOT NULL,
            source_type  TEXT DEFAULT 'Business',
            source_name  TEXT DEFAULT '',
            amount       REAL DEFAULT 0,
            note         TEXT DEFAULT ''
        )
    """)

    # LT — Tax pocket entries
    c.execute("""
        CREATE TABLE IF NOT EXISTS tax_pocket_entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  TEXT NOT NULL,
            amount      REAL DEFAULT 0,
            link_type   TEXT DEFAULT 'Impôt',
            source      TEXT DEFAULT '',
            urgency_level TEXT DEFAULT '',
            status      TEXT DEFAULT 'En attente',
            paid_at     TEXT DEFAULT '',
            note        TEXT DEFAULT ''
        )
    """)

    # Monthly investment logs (per ETF, per month)
    c.execute("""
        CREATE TABLE IF NOT EXISTS monthly_investments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            month_key   TEXT NOT NULL,
            ticker      TEXT NOT NULL,
            amount_eur  REAL DEFAULT 0,
            buy_price   REAL DEFAULT 0,
            parts       REAL DEFAULT 0,
            created_at  TEXT NOT NULL,
            note        TEXT DEFAULT ''
        )
    """)

    # Wallet crypto — avoirs par coin (snapshot manuel, prix live)
    c.execute("""
        CREATE TABLE IF NOT EXISTS crypto_wallet (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            coin    TEXT NOT NULL,
            qty     REAL DEFAULT 0
        )
    """)

    # Fortress One — monthly manual savings history
    c.execute("""
        CREATE TABLE IF NOT EXISTS fortress_savings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            month_key   TEXT NOT NULL UNIQUE,
            amount      REAL DEFAULT 0,
            note        TEXT DEFAULT '',
            created_at  TEXT NOT NULL
        )
    """)

    # Migrate monthly_investments: add buy_price/parts if missing
    for col in ["buy_price REAL DEFAULT 0", "parts REAL DEFAULT 0"]:
        try:
            c.execute(f"ALTER TABLE monthly_investments ADD COLUMN {col}")
        except Exception:
            pass

    # Migrate tax_pocket_entries: add source column if missing
    try:
        c.execute("ALTER TABLE tax_pocket_entries ADD COLUMN source TEXT DEFAULT ''")
    except Exception:
        pass

    # Migrate tax_pocket_entries: add urgency_level column if missing
    try:
        c.execute("ALTER TABLE tax_pocket_entries ADD COLUMN urgency_level TEXT DEFAULT ''")
    except Exception:
        pass

    # Migrate tax_pocket_entries: add status column if missing
    try:
        c.execute("ALTER TABLE tax_pocket_entries ADD COLUMN status TEXT DEFAULT 'En attente'")
    except Exception:
        pass

    # Migrate tax_pocket_entries: add paid_at column if missing
    try:
        c.execute("ALTER TABLE tax_pocket_entries ADD COLUMN paid_at TEXT DEFAULT ''")
    except Exception:
        pass

    # Migrate old finances table if month_key column missing
    try:
        c.execute("ALTER TABLE finances ADD COLUMN month_key TEXT")
        conn.commit()
        c.execute("UPDATE finances SET month_key = substr(date,1,7) WHERE month_key IS NULL OR month_key = ''")
        conn.commit()
    except Exception:
        pass

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


# ── FORTRESS MONTHLY SAVINGS ───────────────────────────────────────────────

def get_fortress_savings_for_month(month_key: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM fortress_savings WHERE month_key=?",
        (month_key,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_fortress_savings_history() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM fortress_savings ORDER BY month_key DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_fortress_saving(month_key: str, amount: float, note: str = "") -> float:
    """Insert/update one monthly saving entry and sync LT capital with delta."""
    amount = float(amount or 0)
    conn = get_connection()
    existing = conn.execute(
        "SELECT amount FROM fortress_savings WHERE month_key=?",
        (month_key,)
    ).fetchone()
    previous_amount = float(existing["amount"]) if existing else 0.0
    now = datetime.now().isoformat(timespec="seconds")

    if existing:
        conn.execute(
            "UPDATE fortress_savings SET amount=?, note=? WHERE month_key=?",
            (amount, note, month_key),
        )
    else:
        conn.execute(
            """
            INSERT INTO fortress_savings (month_key, amount, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (month_key, amount, note, now),
        )

    conn.commit()
    conn.close()

    delta = amount - previous_amount
    return adjust_lt_capital(delta)


def delete_fortress_saving(month_key: str) -> float:
    """Delete one monthly saving entry and remove its amount from LT capital."""
    conn = get_connection()
    row = conn.execute(
        "SELECT amount FROM fortress_savings WHERE month_key=?",
        (month_key,),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM fortress_savings WHERE month_key=?", (month_key,))
    conn.commit()
    conn.close()

    removed = float(row["amount"]) if row else 0.0
    return adjust_lt_capital(-removed)


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

    total_value = sum(float(r.get("shares", 0) or 0) * float(r.get("price", 0) or 0) for r in rows)
    set_setting("lt_invest_bourse", total_value)


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


def get_latest_portfolio_total_value() -> float:
    """Returns total EUR value of all logged monthly ETF investments."""
    return get_total_invested_all_time()


def get_portfolio_holdings() -> dict:
    """Returns total parts held per ticker.

    Priority order:
    1) Latest manual holdings snapshot from portfolio_v2 (source of truth for current parts)
    2) Aggregated parts from monthly_investments history (fallback)
    """
    latest = get_latest_portfolio_v2()
    if latest:
        out = {}
        for r in latest:
            ticker = r.get("ticker")
            shares = float(r.get("shares", 0) or 0)
            price = float(r.get("price", 0) or 0)
            if ticker:
                out[ticker] = {
                    "parts": shares,
                    "invested": shares * price,
                }
        if out:
            return out

    conn = get_connection()
    rows = conn.execute(
        "SELECT ticker, SUM(parts) as total_parts, SUM(amount_eur) as total_invested "
        "FROM monthly_investments GROUP BY ticker"
    ).fetchall()
    conn.close()
    return {r["ticker"]: {"parts": float(r["total_parts"] or 0), "invested": float(r["total_invested"] or 0)} for r in rows}


def get_live_portfolio_value() -> float:
    """Fetch live portfolio value = sum(parts × current_price) for all holdings."""
    holdings = get_portfolio_holdings()
    if not holdings:
        return 0.0
    try:
        import yfinance as yf
        total = 0.0
        for ticker, data in holdings.items():
            if data["parts"] > 0:
                try:
                    hist = yf.Ticker(ticker).history(period="2d")
                    if not hist.empty:
                        price = float(hist["Close"].iloc[-1])
                        total += data["parts"] * price
                except Exception:
                    total += data["invested"]  # fallback to invested amount
        return total
    except ImportError:
        return get_total_invested_all_time()


# ── MONTHLY INVESTMENTS ──────────────────────────────────────────────────────

def save_monthly_investment(month_key: str, investments: list[dict]):
    """
    Save monthly investment log.
    investments = [{"ticker": "SXR8.DE", "amount_eur": 137.50, "buy_price": 600.0, "parts": 0.229}, ...]
    Replaces existing entries for that month.
    """
    conn = get_connection()
    conn.execute("DELETE FROM monthly_investments WHERE month_key=?", (month_key,))
    now = datetime.now().isoformat()
    for inv in investments:
        conn.execute(
            "INSERT INTO monthly_investments (month_key, ticker, amount_eur, buy_price, parts, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (month_key, inv["ticker"], float(inv.get("amount_eur", 0)),
             float(inv.get("buy_price", 0)), float(inv.get("parts", 0)), now),
        )
    conn.commit()
    conn.close()


def get_monthly_investments(month_key: str = None) -> list[dict]:
    """Get investment logs. If month_key given, filter by month."""
    conn = get_connection()
    if month_key:
        rows = conn.execute(
            "SELECT * FROM monthly_investments WHERE month_key=? ORDER BY id", (month_key,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM monthly_investments ORDER BY month_key DESC, id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_investment_totals() -> list[dict]:
    """Get total invested per month."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT month_key, SUM(amount_eur) as total FROM monthly_investments GROUP BY month_key ORDER BY month_key DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_total_invested_all_time() -> float:
    """Get total amount invested across all months."""
    conn = get_connection()
    row = conn.execute("SELECT SUM(amount_eur) as total FROM monthly_investments").fetchone()
    conn.close()
    return float((row["total"] if row else 0) or 0)


def delete_monthly_investment(month_key: str):
    """Delete all investment entries for a given month."""
    conn = get_connection()
    conn.execute("DELETE FROM monthly_investments WHERE month_key=?", (month_key,))
    conn.commit()
    conn.close()


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


def delete_business_test(test_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM business_tests WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()


# ── RISK INVESTMENTS ─────────────────────────────────────────────────────────

def create_risk_investment(name: str, asset_type: str, quantity: float, entry_price: float,
                           note: str = "", deduct_from_lt: bool = False):
    """Create a new risky investment (crypto, speculative stock, etc.)"""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO risk_investments (created_at, name, asset_type, quantity, entry_price, current_price, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (datetime.now().isoformat(), name, asset_type, float(quantity), float(entry_price), float(entry_price), note),
    )
    conn.commit()
    conn.close()
    if deduct_from_lt:
        invested_amount = float(quantity) * float(entry_price)
        if invested_amount > 0:
            adjust_lt_capital(-invested_amount)


def update_risk_investment_price(investment_id: int, current_price: float):
    """Update current price of an investment"""
    conn = get_connection()
    conn.execute(
        "UPDATE risk_investments SET current_price = ? WHERE id = ?",
        (float(current_price), investment_id)
    )
    conn.commit()
    conn.close()


def delete_risk_investment(investment_id: int):
    """Delete a risk investment"""
    conn = get_connection()
    conn.execute("DELETE FROM risk_investments WHERE id = ?", (investment_id,))
    conn.commit()
    conn.close()


def get_risk_investments():
    """Get all risk investments with gains/losses calculated"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM risk_investments ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        invested = float(d['quantity']) * float(d['entry_price'])
        current = float(d['quantity']) * float(d['current_price'])
        gain_loss = current - invested
        gain_loss_pct = (gain_loss / invested * 100) if invested > 0 else 0
        d['invested_amount'] = invested
        d['current_amount'] = current
        d['gain_loss'] = gain_loss
        d['gain_loss_pct'] = gain_loss_pct
        result.append(d)
    return result


def get_risk_investment_totals():
    """Get total invested and current value across all risk investments"""
    conn = get_connection()
    rows = conn.execute("SELECT quantity, entry_price, current_price FROM risk_investments").fetchall()
    conn.close()
    
    total_invested = 0.0
    total_current = 0.0
    
    for r in rows:
        invested = float(r['quantity']) * float(r['entry_price'])
        current = float(r['quantity']) * float(r['current_price'])
        total_invested += invested
        total_current += current
    
    return {
        'total_invested': total_invested,
        'total_current': total_current,
        'gain_loss': total_current - total_invested,
        'gain_loss_pct': ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0
    }


def get_risk_crypto_current_value() -> float:
    """Get current total value for risk investments tagged as crypto."""
    conn = get_connection()
    rows = conn.execute("SELECT asset_type, quantity, current_price FROM risk_investments").fetchall()
    conn.close()

    total_crypto = 0.0
    for r in rows:
        asset_type = str(r["asset_type"] or "").strip().lower()
        if "crypto" in asset_type:
            total_crypto += float(r["quantity"] or 0) * float(r["current_price"] or 0)
    return float(total_crypto)


# ── CT PAYOUTS ──────────────────────────────────────────────────────────────

def create_ct_payout(source_type: str, source_name: str, amount: float, note: str = ""):
    amount = float(amount or 0)
    if amount <= 0:
        return

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO ct_payouts (created_at, source_type, source_name, amount, note)
        VALUES (?, ?, ?, ?, ?)
        """,
        (datetime.now().isoformat(), str(source_type or ""), str(source_name or ""), amount, str(note or "")),
    )
    conn.commit()
    conn.close()
    adjust_lt_capital(amount)


def get_ct_payouts(limit: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ct_payouts ORDER BY created_at DESC LIMIT ?",
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ct_payout_total() -> float:
    conn = get_connection()
    row = conn.execute("SELECT SUM(amount) AS total FROM ct_payouts").fetchone()
    conn.close()
    return float((row["total"] if row else 0) or 0)


# ── TAX POCKET (LT) ─────────────────────────────────────────────────────────

def create_tax_pocket_entry(
    amount: float,
    link_type: str,
    note: str = "",
    source: str = "",
    urgency_level: str = "",
):
    amount = float(amount or 0)
    if amount <= 0:
        return

    link_type = str(link_type or "Impôt")
    source = str(source or "")
    urgency_level = str(urgency_level or "")
    note = str(note or "")

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO tax_pocket_entries (created_at, amount, link_type, source, urgency_level, status, paid_at, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (datetime.now().isoformat(), amount, link_type, source, urgency_level, "En attente", "", note)
    )
    conn.commit()
    conn.close()
    adjust_lt_capital(-amount)


def get_tax_pocket_entries(limit: int = 100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tax_pocket_entries ORDER BY created_at DESC LIMIT ?",
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_tax_pocket_entry(entry_id: int) -> float:
    conn = get_connection()
    row = conn.execute(
        "SELECT amount FROM tax_pocket_entries WHERE id = ?",
        (int(entry_id),),
    ).fetchone()

    if not row:
        conn.close()
        return 0.0

    amount = float(row["amount"] or 0)
    conn.execute("DELETE FROM tax_pocket_entries WHERE id = ?", (int(entry_id),))
    conn.commit()
    conn.close()

    if amount > 0:
        adjust_lt_capital(amount)
    return amount


def mark_tax_pocket_entry_paid(entry_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE tax_pocket_entries SET status = ?, paid_at = ? WHERE id = ?",
        ("Payé", datetime.now().isoformat(), int(entry_id)),
    )
    conn.commit()
    conn.close()


# ── WALLET CRYPTO ────────────────────────────────────────────────────────────

def get_crypto_wallet() -> list[dict]:
    """Retourne les avoirs crypto : [{'coin': 'BTC', 'qty': 0.05}, ...]."""
    conn = get_connection()
    rows = conn.execute("SELECT coin, qty FROM crypto_wallet ORDER BY id").fetchall()
    conn.close()
    return [{"coin": r["coin"], "qty": float(r["qty"] or 0)} for r in rows]


def save_crypto_wallet(rows: list[dict]):
    """Remplace le wallet par les lignes données (coin, qty)."""
    conn = get_connection()
    conn.execute("DELETE FROM crypto_wallet")
    for r in rows:
        coin = (r.get("coin") or "").strip().upper()
        qty = float(r.get("qty", 0) or 0)
        if coin and qty > 0:
            conn.execute("INSERT INTO crypto_wallet (coin, qty) VALUES (?, ?)", (coin, qty))
    conn.commit()
    conn.close()


# ── HISTORIQUE PATRIMOINE (snapshots mensuels) ───────────────────────────────

def record_wealth_snapshot(total: float, epargne: float, bourse: float, crypto: float):
    """Enregistre (ou met à jour) le patrimoine du mois courant. 1 point / mois."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wealth_history (
            month_key TEXT PRIMARY KEY,
            date      TEXT NOT NULL,
            total     REAL DEFAULT 0,
            epargne   REAL DEFAULT 0,
            bourse    REAL DEFAULT 0,
            crypto    REAL DEFAULT 0
        )
    """)
    mk = date.today().strftime("%Y-%m")
    conn.execute("""
        INSERT INTO wealth_history (month_key, date, total, epargne, bourse, crypto)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(month_key) DO UPDATE SET
            date=excluded.date, total=excluded.total,
            epargne=excluded.epargne, bourse=excluded.bourse, crypto=excluded.crypto
    """, (mk, date.today().isoformat(), total, epargne, bourse, crypto))
    conn.commit()
    conn.close()


def get_wealth_history() -> list[dict]:
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wealth_history (
            month_key TEXT PRIMARY KEY, date TEXT NOT NULL,
            total REAL DEFAULT 0, epargne REAL DEFAULT 0,
            bourse REAL DEFAULT 0, crypto REAL DEFAULT 0
        )
    """)
    rows = conn.execute("SELECT * FROM wealth_history ORDER BY month_key").fetchall()
    conn.close()
    return [dict(r) for r in rows]
