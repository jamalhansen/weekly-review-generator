from schema import WeekReview, WeeklyHighlight
from markdown_output import format_as_markdown


class TestFormatAsMarkdown:
    def _make_review(self, **kwargs):
        defaults = {"week_of": "2026-02-23", "word_count_input": 100}
        defaults.update(kwargs)
        return WeekReview(**defaults)

    def test_contains_headline(self):
        review = self._make_review(headline="A great week")
        md = format_as_markdown(review)
        assert "A great week" in md

    def test_contains_week_of(self):
        review = self._make_review()
        md = format_as_markdown(review)
        assert "2026-02-23" in md

    def test_contains_highlight_category(self):
        review = self._make_review(
            highlights=[WeeklyHighlight(category="Work", summary="Built things")]
        )
        md = format_as_markdown(review)
        assert "Work" in md

    def test_contains_links(self):
        review = self._make_review(links_saved=["https://example.com"])
        md = format_as_markdown(review)
        assert "https://example.com" in md

    def test_open_threads_formatted_as_tasks(self):
        review = self._make_review(open_threads=["Write tests"])
        md = format_as_markdown(review)
        assert "- [ ] Write tests" in md

    def test_word_count_in_output(self):
        review = self._make_review(word_count_input=999)
        md = format_as_markdown(review)
        assert "999" in md
