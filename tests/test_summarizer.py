import json
import datetime
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from logic import app
from local_first_common.testing import MockProvider

FIXTURES = Path(__file__).parent / "fixtures"

SAMPLE_RESPONSE = json.dumps({
    "week_of": "2026-02-23",
    "headline": "A very productive week",
    "highlights": [
        {"category": "Work", "summary": "Finished the AI consolidation project.", "items": ["Migrated providers", "Standardized CLI"]}
    ],
    "goal_progress": [],
    "links_saved": ["https://example.com"],
    "open_threads": ["Refactor tests"],
    "word_count_input": 500
})


class TestSummarizeCLI:
    @patch("logic.find_vault_root")
    @patch("logic.resolve_provider")
    @patch("logic.write_review_section")
    def test_summarize_json_output(self, mock_write, mock_resolve, mock_find_vault):
        runner = CliRunner()
        mock_find_vault.return_value = FIXTURES.parent # fixtures are in tests/fixtures
        mock_llm = MockProvider(response=SAMPLE_RESPONSE)
        mock_resolve.return_value = mock_llm
        
        # We need to ensure load_daily_notes_for_week finds something
        # or mock it. Let's mock it to be safe.
        with patch("logic.load_daily_notes_for_week") as mock_load:
            mock_load.return_value = [{"path": "dummy", "content": "dummy content", "date": datetime.date(2026, 2, 23)}]
            result = runner.invoke(app, ["--week", "2026-02-23", "--output", "json"])
            
        assert result.exit_code == 0
        output_json = json.loads(result.output)
        assert output_json["headline"] == "A very productive week"
        assert len(mock_llm.calls) == 1

    @patch("logic.find_vault_root")
    @patch("logic.resolve_provider")
    def test_summarize_dry_run(self, mock_resolve, mock_find_vault):
        runner = CliRunner()
        mock_find_vault.return_value = FIXTURES.parent
        mock_llm = MockProvider(response=SAMPLE_RESPONSE)
        mock_resolve.return_value = mock_llm
        
        with patch("logic.load_daily_notes_for_week") as mock_load:
            mock_load.return_value = [{"path": "dummy", "content": "dummy content", "date": datetime.date(2026, 2, 23)}]
            result = runner.invoke(app, ["--week", "2026-02-23", "--dry-run"])
            
        assert result.exit_code == 0
        assert "A very productive week" in result.output
        assert len(mock_llm.calls) == 1
