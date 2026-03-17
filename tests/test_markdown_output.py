

from schema import WeekReview, WeeklyHighlight
from markdown_output import format_as_markdown, format_review_section, write_review_section


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


class TestFormatReviewSection:
    def _make_review(self, **kwargs):
        defaults = {"week_of": "2026-02-23", "word_count_input": 100}
        defaults.update(kwargs)
        return WeekReview(**defaults)

    def test_contains_headline_as_blockquote(self):
        review = self._make_review(headline="A great week")
        section = format_review_section(review)
        assert "> A great week" in section

    def test_uses_h3_for_highlights(self):
        review = self._make_review(
            highlights=[WeeklyHighlight(category="Work", summary="Built things")]
        )
        section = format_review_section(review)
        assert "### Highlights" in section
        assert "**Work**" in section

    def test_open_threads_formatted_as_tasks(self):
        review = self._make_review(open_threads=["Follow up on PR"])
        section = format_review_section(review)
        assert "- [ ] Follow up on PR" in section

    def test_links_saved_included(self):
        review = self._make_review(links_saved=["https://example.com"])
        section = format_review_section(review)
        assert "https://example.com" in section

    def test_word_count_footer(self):
        review = self._make_review(word_count_input=500)
        section = format_review_section(review)
        assert "500" in section


class TestWriteReviewSection:
    def _make_review_content(self):
        return "> A great week\n\n### Highlights\n**Work** — did things\n"

    def test_creates_file_from_fallback_when_no_template(self, tmp_path):
        file_path = tmp_path / "2026-W11.md"
        write_review_section(file_path, self._make_review_content())
        assert file_path.exists()
        content = file_path.read_text()
        assert "## Review" in content

    def test_creates_file_from_template(self, tmp_path):
        template = tmp_path / "Weekly Note.md"
        template.write_text("## Intention\n1. \n\n## Review\n\n")
        file_path = tmp_path / "2026-W11.md"
        write_review_section(file_path, self._make_review_content(), template_path=template)
        assert file_path.exists()
        content = file_path.read_text()
        assert "## Intention" in content
        assert "## Review" in content

    def test_writes_review_content_into_section(self, tmp_path):
        file_path = tmp_path / "2026-W11.md"
        file_path.write_text("## Intention\n1. item\n\n## Review\n\nold content\n")
        write_review_section(file_path, "> New review")
        content = file_path.read_text()
        assert "> New review" in content
        assert "old content" not in content

    def test_preserves_intention_section(self, tmp_path):
        file_path = tmp_path / "2026-W11.md"
        file_path.write_text("## Intention\n1. My goal\n\n## Review\n\n")
        write_review_section(file_path, "> New review")
        content = file_path.read_text()
        assert "My goal" in content

    def test_preserves_sections_after_review(self, tmp_path):
        file_path = tmp_path / "2026-W11.md"
        file_path.write_text("## Intention\n1. \n\n## Review\n\n## Next Week\n- plan\n")
        write_review_section(file_path, "> New review")
        content = file_path.read_text()
        assert "## Next Week" in content
        assert "- plan" in content

    def test_adds_review_section_if_missing(self, tmp_path):
        file_path = tmp_path / "2026-W11.md"
        file_path.write_text("## Intention\n1. item\n")
        write_review_section(file_path, "> Added")
        content = file_path.read_text()
        assert "## Review" in content
        assert "> Added" in content
