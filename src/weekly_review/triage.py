from datetime import date
from local_first_common.db import get_db_cursor

def get_triage_captures(db_path: str, start_date: date, end_date: date) -> list[dict]:
    """Return executed capture threads from the triage DB for the given date range.

    Queries thread_triage for rows where human_disposition='capture' and
    executed_at falls within [start_date, end_date] (inclusive).
    Returns a list of dicts with keys: thread_text, suggested_action.
    Returns an empty list if the DB doesn't exist (graceful no-op).
    """
    try:
        with get_db_cursor(db_path) as cur:
            if cur is None:
                return []
            
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
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        raise RuntimeError(f"Failed to query triage DB at {db_path}: {e}")
