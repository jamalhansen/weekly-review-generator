import calendar
import datetime
import re

from local_first_common.obsidian import get_week_dates

from .schema import WeekReview


class WeeklyReviewError(Exception):
    """Base typed error for weekly-review-generator."""


class ProviderSetupError(WeeklyReviewError):
    """Raised when provider resolution fails."""


class LLMRunError(WeeklyReviewError):
    """Raised when the LLM review generation call fails."""


def strip_obsidian_callouts(text: str) -> str:
    """Convert Obsidian callout blocks to plain prose for LLM consumption."""
    lines = text.splitlines()
    result = []
    for line in lines:
        if re.match(r"^>\s*\[!", line):
            continue
        stripped = re.sub(r"^>\s?", "", line)
        result.append(stripped)
    return "\n".join(result)


def get_word_count(text: str) -> int:
    return len(text.split())


def get_date_range(
    target_date: datetime.date,
    days: int | None = None,
    month: bool = False,
) -> list[datetime.date]:
    """Return the list of dates for the review period."""
    if month:
        _, last_day = calendar.monthrange(target_date.year, target_date.month)
        start = target_date.replace(day=1)
        end = target_date.replace(day=last_day)
        return [start + datetime.timedelta(i) for i in range((end - start).days + 1)]
    if days is not None:
        start = target_date - datetime.timedelta(days=days - 1)
        return [start + datetime.timedelta(i) for i in range(days)]
    return get_week_dates(target_date)


def get_output_filename(
    target_date: datetime.date,
    dates: list[datetime.date],
    days: int | None,
    month: bool,
) -> str:
    if month:
        return f"{target_date.year}-{target_date.month:02d}.md"
    if days is not None:
        return f"{dates[0].isoformat()}--{dates[-1].isoformat()}.md"
    iso_year, iso_week, _ = target_date.isocalendar()
    return f"{iso_year}-W{iso_week:02d}.md"


def process_llm_response(
    response_data, period_start: str, word_count: int
) -> WeekReview:
    """Post-process and validate LLM response data."""
    if hasattr(response_data, "model_dump"):
        response_data = response_data.model_dump()
    response_data["week_of"] = period_start
    response_data["word_count_input"] = word_count

    raw_highlights = response_data.get("highlights", [])
    if raw_highlights:
        grouped = {}
        for h in raw_highlights:
            cat = h.get("category", "Other")
            if cat not in grouped:
                grouped[cat] = {
                    "category": cat,
                    "summary": h.get("summary", ""),
                    "items": h.get("items", []) or [],
                }
            else:
                if h.get("summary"):
                    grouped[cat]["summary"] += " " + h["summary"]
                if h.get("items"):
                    grouped[cat]["items"].extend(h["items"])
        response_data["highlights"] = list(grouped.values())

    return WeekReview(**response_data)
