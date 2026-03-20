import sqlite3
from datetime import date


def get_kept_items(db_path: str, start_date: date, end_date: date) -> list[dict]:
    """Return kept content discovery items for the given date range.

    Queries the content discovery SQLite DB for items with status='kept'
    whose fetched_at falls within [start_date, end_date] (inclusive).
    Returns a list of dicts with keys: title, url, summary, tags, score.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT title, url, summary, tags, score
            FROM items
            WHERE status = 'kept'
              AND fetched_at BETWEEN ? AND ?
            ORDER BY score DESC
            """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        raise RuntimeError(f"Failed to query content discovery DB at {db_path}: {e}")
