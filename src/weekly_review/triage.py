import sqlite3
from datetime import date
from pathlib import Path


def get_triage_captures(db_path: str, start_date: date, end_date: date) -> list[dict]:
    """Return executed capture threads from the triage DB for the given date range.

    Queries thread_triage for rows where human_disposition='capture' and
    executed_at falls within [start_date, end_date] (inclusive).
    Returns a list of dicts with keys: thread_text, suggested_action.
    Returns an empty list if the DB doesn't exist (graceful no-op).
    """
    p = Path(db_path).expanduser()
    if not p.exists():
        return []
    try:
        conn = sqlite3.connect(str(p))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT thread_text, suggested_action
            FROM thread_triage
            WHERE human_disposition = 'capture'
              AND date(executed_at) BETWEEN ? AND ?
            ORDER BY executed_at
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        raise RuntimeError(f"Failed to query triage DB at {db_path}: {e}")
