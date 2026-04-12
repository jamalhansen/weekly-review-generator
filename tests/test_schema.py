import pytest
from pydantic import ValidationError

from weekly_review.schema import WeekReview, WeeklyHighlight


class TestWeeklyHighlight:
    def test_valid_highlight(self):
        h = WeeklyHighlight(category="Work", summary="A good week", items=["item1"])
        assert h.category == "Work"

    def test_defaults(self):
        h = WeeklyHighlight(category="Personal")
        assert h.summary == ""
        assert h.items == []


class TestWeekReview:
    def test_valid_review(self):
        review = WeekReview(week_of="2026-02-23", word_count_input=500)
        assert review.week_of == "2026-02-23"
        assert review.word_count_input == 500

    def test_defaults(self):
        review = WeekReview(week_of="2026-02-23", word_count_input=0)
        assert review.headline == "Weekly Summary"
        assert review.highlights == []
        assert review.links_saved == []
        assert review.suggested_intentions == []

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            WeekReview()

    def test_full_review(self):
        review = WeekReview(
            week_of="2026-02-23",
            headline="A productive week",
            highlights=[WeeklyHighlight(category="Work", summary="Built things")],
            links_saved=["https://example.com"],
            suggested_intentions=["Finish API doc"],
            word_count_input=1234,
        )
        assert len(review.highlights) == 1
        assert review.links_saved[0] == "https://example.com"
