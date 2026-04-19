import sqlite3
import datetime
from pathlib import Path

import pytest

from weekly_review.triage import get_triage_captures, TriageDBError


class TestTypedErrors:
    def test_triage_db_error_is_exception(self):
        err = TriageDBError("connection refused")
        assert "connection refused" in str(err)
        assert isinstance(err, Exception)


def make_triage_db(tmp_path: Path, rows: list[dict]) -> str:
    db_path = str(tmp_path / "thread-triage.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE thread_triage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week TEXT,
            source_file TEXT,
            thread_text TEXT,
            thread_type TEXT DEFAULT 'task',
            human_disposition TEXT,
            suggested_action TEXT,
            executed_at TEXT,
            resurface_after TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    for row in rows:
        conn.execute(
            """INSERT INTO thread_triage
               (week, source_file, thread_text, thread_type, human_disposition, suggested_action, executed_at)
               VALUES (:week, :source_file, :thread_text, :thread_type, :human_disposition, :suggested_action, :executed_at)""",
            row,
        )
    conn.commit()
    conn.close()
    return db_path


SAMPLE_ROWS = [
    {
        "week": "2026-W11",
        "source_file": "a.md",
        "thread_text": "Write a blog post about local-first AI",
        "thread_type": "thought",
        "human_disposition": "capture",
        "suggested_action": "Draft outline in Obsidian",
        "executed_at": "2026-03-10 10:00:00",
    },
    {
        "week": "2026-W11",
        "source_file": "b.md",
        "thread_text": "Research vector embeddings for search",
        "thread_type": "thought",
        "human_disposition": "capture",
        "suggested_action": "Add to reading list",
        "executed_at": "2026-03-12 09:00:00",
    },
    {
        "week": "2026-W11",
        "source_file": "c.md",
        "thread_text": "This is a task to discard",
        "thread_type": "task",
        "human_disposition": "discard",
        "suggested_action": None,
        "executed_at": "2026-03-11 08:00:00",
    },
    {
        "week": "2026-W10",
        "source_file": "d.md",
        "thread_text": "Old capture from last week",
        "thread_type": "thought",
        "human_disposition": "capture",
        "suggested_action": "Archive",
        "executed_at": "2026-03-03 10:00:00",
    },
    {
        "week": "2026-W11",
        "source_file": "e.md",
        "thread_text": "Pending — not yet executed",
        "thread_type": "thought",
        "human_disposition": "capture",
        "suggested_action": None,
        "executed_at": None,
    },
]


class TestGetTriageCaptures:
    def test_returns_capture_rows_in_range(self, tmp_path):
        db_path = make_triage_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 14)
        items = get_triage_captures(db_path, start, end)
        texts = [i["thread_text"] for i in items]
        assert "Write a blog post about local-first AI" in texts
        assert "Research vector embeddings for search" in texts

    def test_excludes_non_capture_dispositions(self, tmp_path):
        db_path = make_triage_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 14)
        items = get_triage_captures(db_path, start, end)
        texts = [i["thread_text"] for i in items]
        assert "This is a task to discard" not in texts

    def test_excludes_out_of_range_rows(self, tmp_path):
        db_path = make_triage_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 14)
        items = get_triage_captures(db_path, start, end)
        texts = [i["thread_text"] for i in items]
        assert "Old capture from last week" not in texts

    def test_excludes_rows_with_null_executed_at(self, tmp_path):
        db_path = make_triage_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 14)
        items = get_triage_captures(db_path, start, end)
        texts = [i["thread_text"] for i in items]
        assert "Pending — not yet executed" not in texts

    def test_result_has_expected_keys(self, tmp_path):
        db_path = make_triage_db(tmp_path, SAMPLE_ROWS)
        items = get_triage_captures(
            db_path, datetime.date(2026, 3, 9), datetime.date(2026, 3, 14)
        )
        assert len(items) > 0
        for item in items:
            assert set(item.keys()) == {"thread_text", "suggested_action"}

    def test_returns_empty_list_when_db_missing(self, tmp_path):
        result = get_triage_captures(
            str(tmp_path / "nonexistent.db"),
            datetime.date(2026, 3, 9),
            datetime.date(2026, 3, 14),
        )
        assert result == []

    def test_returns_empty_list_when_no_matches(self, tmp_path):
        db_path = make_triage_db(tmp_path, SAMPLE_ROWS)
        result = get_triage_captures(
            db_path, datetime.date(2025, 1, 1), datetime.date(2025, 1, 7)
        )
        assert result == []

    def test_raises_on_bad_db(self, tmp_path):
        bad_db = tmp_path / "bad.db"
        bad_db.write_text("not a sqlite file")
        with pytest.raises(TriageDBError, match="Failed to query"):
            get_triage_captures(
                str(bad_db), datetime.date(2026, 3, 9), datetime.date(2026, 3, 14)
            )
