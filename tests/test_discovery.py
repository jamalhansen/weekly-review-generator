import sqlite3
import datetime
from pathlib import Path

import pytest

from weekly_review.discovery import get_kept_items, DiscoveryDBError


class TestTypedErrors:
    def test_discovery_db_error_is_exception(self):
        err = DiscoveryDBError("db gone")
        assert "db gone" in str(err)
        assert isinstance(err, Exception)


def make_db(tmp_path: Path, rows: list[dict]) -> str:
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE items (
            title TEXT, url TEXT, summary TEXT, tags TEXT, score REAL,
            status TEXT, fetched_at TEXT, reviewed_at TEXT, source TEXT
        )"""
    )
    for row in rows:
        conn.execute(
            "INSERT INTO items VALUES (:title, :url, :summary, :tags, :score, :status, :fetched_at, :reviewed_at, :source)",
            row,
        )
    conn.commit()
    conn.close()
    return db_path


SAMPLE_ROWS = [
    {
        "title": "Article A",
        "url": "https://example.com/a",
        "summary": "Summary A",
        "tags": '["tech","ai"]',
        "score": 0.9,
        "status": "kept",
        "fetched_at": "2026-03-10",
        "reviewed_at": "2026-03-10",
        "source": "TechBlog",
    },
    {
        "title": "Article B",
        "url": "https://example.com/b",
        "summary": "Summary B",
        "tags": '["science"]',
        "score": 0.7,
        "status": "kept",
        "fetched_at": "2026-03-11",
        "reviewed_at": "2026-03-11",
        "source": "ScienceDaily",
    },
    {
        "title": "Article C - skipped",
        "url": "https://example.com/c",
        "summary": "Summary C",
        "tags": "[]",
        "score": 0.5,
        "status": "new",
        "fetched_at": "2026-03-10",
        "reviewed_at": None,
        "source": "Unknown",
    },
    {
        "title": "Article D - out of range",
        "url": "https://example.com/d",
        "summary": "Summary D",
        "tags": "[]",
        "score": 0.8,
        "status": "kept",
        "fetched_at": "2026-03-01",
        "reviewed_at": "2026-03-01",
        "source": "OldNews",
    },
]


class TestGetKeptItems:
    def test_returns_kept_items_in_range(self, tmp_path):
        db_path = make_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 12)
        items = get_kept_items(db_path, start, end)
        assert len(items) == 2
        titles = [i["title"] for i in items]
        assert "Article A" in titles
        assert "Article B" in titles

    def test_excludes_non_kept_items(self, tmp_path):
        db_path = make_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 12)
        items = get_kept_items(db_path, start, end)
        titles = [i["title"] for i in items]
        assert "Article C - skipped" not in titles

    def test_excludes_out_of_range_items(self, tmp_path):
        db_path = make_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 12)
        items = get_kept_items(db_path, start, end)
        titles = [i["title"] for i in items]
        assert "Article D - out of range" not in titles

    def test_returns_empty_list_when_no_matches(self, tmp_path):
        db_path = make_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2025, 1, 1)
        end = datetime.date(2025, 1, 7)
        items = get_kept_items(db_path, start, end)
        assert items == []

    def test_items_ordered_by_date(self, tmp_path):
        db_path = make_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 12)
        items = get_kept_items(db_path, start, end)
        sources = [i["source"] for i in items]
        assert len(sources) == 2

    def test_result_has_expected_keys(self, tmp_path):
        db_path = make_db(tmp_path, SAMPLE_ROWS)
        start = datetime.date(2026, 3, 9)
        end = datetime.date(2026, 3, 12)
        items = get_kept_items(db_path, start, end)
        assert len(items) > 0
        for item in items:
            assert set(item.keys()) == {"title", "url", "summary", "tags", "source"}

    def test_raises_on_invalid_db(self, tmp_path):
        # Pass a directory instead of a file to trigger sqlite error
        with pytest.raises(DiscoveryDBError, match="Failed to query"):
            get_kept_items(str(tmp_path), datetime.date.today(), datetime.date.today())

    def test_inclusive_date_boundaries(self, tmp_path):
        db_path = make_db(tmp_path, SAMPLE_ROWS)
        # Both boundary dates should be included
        items_start = get_kept_items(
            db_path, datetime.date(2026, 3, 10), datetime.date(2026, 3, 10)
        )
        assert len(items_start) == 1
        assert items_start[0]["title"] == "Article A"
