from datetime import date
from local_first_common.db import get_db_cursor


class DiscoveryDBError(Exception):
    """Raised when a content discovery DB query fails."""


def get_kept_items(db_path: str, start_date: date, end_date: date) -> list[dict]:
    """Return kept content discovery items for the given date range.

    Queries the content discovery database for items with status='kept'
    where reviewed_at falls within the target week.
    Returns a list of dicts with keys: title, url, tags, summary.
    Returns an empty list if the DB doesn't exist.
    """
    try:
        with get_db_cursor(db_path) as cur:
            if cur is None:
                return []

            cur.execute(
                """
                SELECT title, url, tags, summary, source
                FROM items
                WHERE status = 'kept'
                  AND date(reviewed_at) BETWEEN ? AND ?
                ORDER BY reviewed_at
                """,
                (start_date.isoformat(), end_date.isoformat()),
            )
            return [dict(row) for row in cur.fetchall()]
    except DiscoveryDBError:
        raise
    except Exception as e:
        raise DiscoveryDBError(
            f"Failed to query content discovery DB at {db_path}: {e}"
        ) from e
