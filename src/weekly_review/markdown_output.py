import datetime
import re
from pathlib import Path
from typing import Optional

from .schema import WeekReview


def _generate_weekly_frontmatter(file_path: Path) -> Optional[str]:
    """Generate correct YAML frontmatter for a weekly note from its filename.

    Returns None if the filename doesn't match the YYYY-WNN pattern (e.g. monthly notes),
    so the caller can fall back to the Obsidian template or a plain default.
    """
    match = re.match(r"(\d{4})-W(\d{2})$", file_path.stem)
    if not match:
        return None

    year, week = int(match.group(1)), int(match.group(2))
    monday = datetime.date.fromisocalendar(year, week, 1)
    prev = monday - datetime.timedelta(weeks=1)
    nxt = monday + datetime.timedelta(weeks=1)
    prev_y, prev_w, _ = prev.isocalendar()
    next_y, next_w, _ = nxt.isocalendar()
    month_str = monday.strftime("%Y-%m")

    return (
        f"---\n"
        f'Week: "{year}-W{week:02d}"\n'
        f'Month: "[[{month_str}]]"\n'
        f'Previous: "[[{prev_y}-W{prev_w:02d}]]"\n'
        f'Next: "[[{next_y}-W{next_w:02d}]]"\n'
        f'Category: "[[Weekly Note]]"\n'
        f"---\n\n"
        f"## Intention\n1. \n2. \n3. \n\n## Review\n\n"
    )


def format_review_section(review: WeekReview) -> str:
    """Format review content for the ## Review section of a weekly note.

    Uses ### sub-headings to nest inside the existing ## Review heading.
    """
    lines = []
    if review.headline:
        lines.append(f"> {review.headline}\n")

    if review.key_insight:
        lines.append("### Key Insight")
        lines.append(f"{review.key_insight}\n")

    if review.highlights:
        lines.append("### Highlights")
        for highlight in review.highlights:
            lines.append(f"**{highlight.category}**")
            if highlight.summary:
                lines.append(f"_{highlight.summary}_")
            if highlight.items:
                for item in highlight.items:
                    lines.append(f"- {item}")
            lines.append("")

    if review.links_saved:
        lines.append("### Links Saved")
        for link in review.links_saved:
            lines.append(f"- {link}")
        lines.append("")

    if review.suggested_intentions:
        lines.append("### Intentions for Next Week")
        for intention in review.suggested_intentions:
            lines.append(f"- {intention}")
        lines.append("")

    lines.append(f"_Generated from {review.word_count_input} words of input._")
    return "\n".join(lines)


def write_review_section(
    file_path: Path,
    review_content: str,
    template_path: Optional[Path] = None,
) -> None:
    """Write review_content into the ## Review section of file_path.

    Creates the file from template_path if it doesn't exist.
    Replaces any existing content under ## Review while preserving
    other sections (e.g. ## Intention).
    """
    if not file_path.exists():
        # Generate proper frontmatter for weekly notes (YYYY-WNN).
        # The Obsidian template uses Templater syntax that Python can't evaluate,
        # so we compute the correct values directly from the filename instead.
        base = _generate_weekly_frontmatter(file_path)
        if base is None:
            # Non-weekly file (e.g. monthly): fall back to template or plain default
            if template_path and template_path.exists():
                base = template_path.read_text()
            else:
                base = "## Intention\n1. \n2. \n3. \n\n## Review\n\n"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(base)

    content = file_path.read_text()

    review_heading = "\n## Review\n"
    if review_heading not in content:
        # Append the section if it's somehow missing
        content = content.rstrip() + "\n\n## Review\n\n"

    before, _, after = content.partition(review_heading)

    # Preserve any sections that follow ## Review
    next_section = ""
    if "\n## " in after:
        idx = after.index("\n## ")
        next_section = after[idx:]

    new_content = before + review_heading + "\n" + review_content.strip() + "\n" + next_section
    file_path.write_text(new_content)


def format_as_markdown(review: WeekReview) -> str:
    """Format the week review as Obsidian-compatible Markdown."""
    lines = []
    lines.append(f"# Weekly Review: {review.week_of}")
    lines.append(f"\n> {review.headline}\n")

    if review.key_insight:
        lines.append("## Key Insight")
        lines.append(f"{review.key_insight}\n")

    if review.highlights:
        lines.append("## Highlights")
        for highlight in review.highlights:
            lines.append(f"### {highlight.category}")
            lines.append(f"_{highlight.summary}_")
            if highlight.items:
                for item in highlight.items:
                    lines.append(f"- {item}")
            lines.append("")

    if review.links_saved:
        lines.append("## Links Saved")
        for link in review.links_saved:
            lines.append(f"- {link}")
        lines.append("")

    if review.suggested_intentions:
        lines.append("## Intentions for Next Week")
        for intention in review.suggested_intentions:
            lines.append(f"- {intention}")
        lines.append("")

    lines.append("---")
    lines.append(f"**Word Count Input:** {review.word_count_input}")
    
    return "\n".join(lines)
