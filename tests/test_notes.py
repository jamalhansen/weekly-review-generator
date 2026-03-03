import datetime
from pathlib import Path

import pytest

from notes import get_week_dates, load_notes_for_week, format_notes_for_llm, get_word_count


FIXTURES = Path(__file__).parent / "fixtures"


class TestGetWeekDates:
    def test_returns_seven_dates(self):
        dates = get_week_dates(datetime.date(2026, 2, 25))
        assert len(dates) == 7

    def test_starts_on_monday(self):
        dates = get_week_dates(datetime.date(2026, 2, 25))
        assert dates[0].weekday() == 0  # Monday

    def test_ends_on_sunday(self):
        dates = get_week_dates(datetime.date(2026, 2, 25))
        assert dates[-1].weekday() == 6  # Sunday

    def test_wednesday_input_still_starts_monday(self):
        dates = get_week_dates(datetime.date(2026, 2, 25))
        assert dates[0] == datetime.date(2026, 2, 23)

    def test_monday_input_unchanged(self):
        dates = get_week_dates(datetime.date(2026, 2, 23))
        assert dates[0] == datetime.date(2026, 2, 23)


class TestLoadNotesForWeek:
    def test_loads_existing_fixture_notes(self, tmp_path):
        # Copy fixtures into a Timeline folder inside tmp_path
        timeline = tmp_path / "Timeline"
        timeline.mkdir()
        for f in FIXTURES.glob("*.md"):
            (timeline / f.name).write_text(f.read_text())

        dates = get_week_dates(datetime.date(2026, 2, 23))
        notes = load_notes_for_week(tmp_path, dates)
        assert len(notes) == 2

    def test_returns_empty_list_for_missing_notes(self, tmp_path):
        (tmp_path / "Timeline").mkdir()
        dates = get_week_dates(datetime.date(2025, 1, 6))
        notes = load_notes_for_week(tmp_path, dates)
        assert notes == []

    def test_note_has_expected_keys(self, tmp_path):
        timeline = tmp_path / "Timeline"
        timeline.mkdir()
        for f in FIXTURES.glob("*.md"):
            (timeline / f.name).write_text(f.read_text())

        dates = get_week_dates(datetime.date(2026, 2, 23))
        notes = load_notes_for_week(tmp_path, dates)
        assert all("date" in n and "content" in n and "path" in n for n in notes)

    def test_falls_back_to_vault_root_when_no_timeline(self, tmp_path):
        (tmp_path / "2026-02-23.md").write_text("hello")
        dates = [datetime.date(2026, 2, 23)]
        notes = load_notes_for_week(tmp_path, dates)
        assert len(notes) == 1


class TestFormatNotesForLlm:
    def test_includes_date_header(self):
        notes = [{"date": datetime.date(2026, 2, 23), "content": "Some content", "path": Path("x.md")}]
        result = format_notes_for_llm(notes)
        assert "DATE: 2026-02-23" in result

    def test_includes_content(self):
        notes = [{"date": datetime.date(2026, 2, 23), "content": "My note text", "path": Path("x.md")}]
        result = format_notes_for_llm(notes)
        assert "My note text" in result

    def test_separates_multiple_notes(self):
        notes = [
            {"date": datetime.date(2026, 2, 23), "content": "Day one", "path": Path("a.md")},
            {"date": datetime.date(2026, 2, 24), "content": "Day two", "path": Path("b.md")},
        ]
        result = format_notes_for_llm(notes)
        assert "Day one" in result and "Day two" in result


class TestGetWordCount:
    def test_counts_words(self):
        assert get_word_count("hello world foo") == 3

    def test_empty_string(self):
        assert get_word_count("") == 0

    def test_multiple_spaces(self):
        assert get_word_count("  one   two  ") == 2
