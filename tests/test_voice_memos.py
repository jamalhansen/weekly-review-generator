import datetime
from pathlib import Path


from voice_memos import get_voice_memos


def make_memos(tmp_path: Path, files: dict[str, str]) -> Path:
    """Write filename -> content pairs into tmp_path."""
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    return tmp_path


class TestGetVoiceMemos:
    def test_returns_memos_in_range(self, tmp_path):
        make_memos(tmp_path, {
            "2026-03-10-morning.md": "Thought about the project.",
            "2026-03-11-evening.md": "Wrapped up the week.",
        })
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert len(result) == 2

    def test_excludes_out_of_range_files(self, tmp_path):
        make_memos(tmp_path, {
            "2026-03-05-old.md": "Old memo.",
            "2026-03-10-current.md": "Current memo.",
        })
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert len(result) == 1
        assert "Current memo." in result[0]

    def test_returns_empty_for_missing_directory(self, tmp_path):
        result = get_voice_memos(str(tmp_path / "nonexistent"), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert result == []

    def test_returns_empty_when_no_matching_files(self, tmp_path):
        make_memos(tmp_path, {"2026-01-01-old.md": "Old."})
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert result == []

    def test_ignores_non_md_txt_files(self, tmp_path):
        make_memos(tmp_path, {
            "2026-03-10-memo.md": "Valid memo.",
            "2026-03-10-audio.mp3": "binary",
            "2026-03-10-notes.txt": "Also valid.",
        })
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert len(result) == 2

    def test_ignores_files_with_unparseable_dates(self, tmp_path):
        make_memos(tmp_path, {
            "not-a-date.md": "Should be ignored.",
            "2026-03-10-valid.md": "Should be included.",
        })
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert len(result) == 1
        assert "Should be included." in result[0]

    def test_returns_file_contents(self, tmp_path):
        make_memos(tmp_path, {"2026-03-10-memo.md": "Meeting went well."})
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert result == ["Meeting went well."]

    def test_inclusive_date_boundaries(self, tmp_path):
        make_memos(tmp_path, {
            "2026-03-09-start.md": "First day.",
            "2026-03-12-end.md": "Last day.",
        })
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert len(result) == 2

    def test_results_sorted_by_filename(self, tmp_path):
        make_memos(tmp_path, {
            "2026-03-11-b.md": "Second.",
            "2026-03-10-a.md": "First.",
        })
        result = get_voice_memos(str(tmp_path), datetime.date(2026, 3, 9), datetime.date(2026, 3, 12))
        assert result[0] == "First."
        assert result[1] == "Second."
