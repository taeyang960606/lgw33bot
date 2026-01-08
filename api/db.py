import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "lgw33.db"

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
      user_id INTEGER PRIMARY KEY,
      username TEXT,
      available INTEGER NOT NULL DEFAULT 0,
      frozen INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      last_active TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
      room_id TEXT PRIMARY KEY,
      chat_id INTEGER,
      host_id INTEGER NOT NULL,
      host_username TEXT,
      guest_id INTEGER,
      guest_username TEXT,
      bet_amount INTEGER NOT NULL,
      status TEXT NOT NULL, -- OPEN, FULL, COUNTDOWN, PLAYING, FINISHED, CANCELLED
      invite_token TEXT NOT NULL,
      host_ready INTEGER NOT NULL DEFAULT 0,
      guest_ready INTEGER NOT NULL DEFAULT 0,
      host_clicks INTEGER NOT NULL DEFAULT 0,
      guest_clicks INTEGER NOT NULL DEFAULT 0,
      countdown_start_time TEXT,
      game_start_time TEXT,
      game_end_time TEXT,
      winner_id INTEGER,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      expires_at TEXT NOT NULL
    );
    """)

    # 添加 countdown_start_time 列（如果不存在）
    try:
        cur.execute("ALTER TABLE rooms ADD COLUMN countdown_start_time TEXT")
    except sqlite3.OperationalError:
        pass  # 列已存在

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger (
      tx_id TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      type TEXT NOT NULL, -- CREDIT, DEBIT, FREEZE, UNFREEZE
      amount INTEGER NOT NULL,
      ref TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    conn.commit()
    conn.close()
