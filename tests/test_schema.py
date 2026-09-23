import pytest
from pydantic import ValidationError

from weekly_review.schema import WeeklyHighlight, WeekReview


class TestWeeklyHighlight:
    def test_valid_highlight(self):
        h = WeeklyHighlight(category="Work", summary="A good week", items=["item1"])
        assert h.category == "Work"

    def test_defaults(self):
        h = WeeklyHighlight(category="Personal")
        assert h.summary == ""
        assert h.items == []

    def test_bare_string_items_coerced_to_single_item_list(self):
        """phi4-mini has returned a bare string for a list[str] field in
        production -- confirmed live 2026-09-20."""
        h = WeeklyHighlight(category="Work", items="Shipped the thing")
        assert h.items == ["Shipped the thing"]


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

    def test_bare_string_links_saved_coerced_to_single_item_list(self):
        """Regression 2026-09-20: phi4-mini returned a plain string for
        links_saved on a real run, which pydantic rejected outright and
        silently dropped that week's review. A bare string is what the
        model meant as a one-item list, not an invalid response."""
        review = WeekReview(
            week_of="2026-02-23",
            links_saved="http://192.168.86.21:8422",
            word_count_input=100,
        )
        assert review.links_saved == ["http://192.168.86.21:8422"]

    def test_bare_string_suggested_intentions_coerced_to_single_item_list(self):
        review = WeekReview(
            week_of="2026-02-23",
            suggested_intentions="Review the effectiveness of language learning tools.",
            word_count_input=100,
        )
        assert review.suggested_intentions == ["Review the effectiveness of language learning tools."]
