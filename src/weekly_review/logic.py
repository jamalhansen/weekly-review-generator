import calendar
import datetime
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

from local_first_common.providers import PROVIDERS
from local_first_common.cli import (
    dry_run_option,
    no_llm_option,
    verbose_option,
    debug_option,
    resolve_provider,
)
from local_first_common.tracking import timed_run
from local_first_common.obsidian import (
    find_vault_root,
    load_daily_notes_for_week,
    format_notes_for_llm,
    get_week_dates,
)
from .schema import WeekReview
from .prompts import get_system_prompt, get_user_prompt
from .display import display_week_review
from .markdown_output import format_review_section, write_review_section, format_as_markdown
from .discovery import get_kept_items
from .triage import get_triage_captures
from .voice_memos import get_voice_memos

app = typer.Typer()

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
    days: Optional[int] = None,
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
    days: Optional[int],
    month: bool,
) -> str:
    if month:
        return f"{target_date.year}-{target_date.month:02d}.md"
    if days is not None:
        return f"{dates[0].isoformat()}--{dates[-1].isoformat()}.md"
    iso_year, iso_week, _ = target_date.isocalendar()
    return f"{iso_year}-W{iso_week:02d}.md"


def process_llm_response(response_data: dict, period_start: str, word_count: int) -> WeekReview:
    """Post-process and validate LLM response data."""
    if not isinstance(response_data, dict):
        raise ValueError("Unexpected response format from LLM.")

    response_data["week_of"] = period_start
    response_data["word_count_input"] = word_count

    raw_highlights = response_data.get("highlights", [])
    if raw_highlights:
        grouped = {}
        for h in raw_highlights:
            cat = h.get("category", "Other")
            if cat not in grouped:
                grouped[cat] = {"category": cat, "summary": h.get("summary", ""), "items": h.get("items", []) or []}
            else:
                if h.get("summary"):
                    grouped[cat]["summary"] += " " + h["summary"]
                if h.get("items"):
                    grouped[cat]["items"].extend(h["items"])
        response_data["highlights"] = list(grouped.values())

    return WeekReview(**response_data)

@app.command()
def summarize(
    week: Annotated[
        Optional[str],
        typer.Option("--week", "-w", help="ISO date in target period (default: today)"),
    ] = None,
    provider: Annotated[str, typer.Option("--provider", "-p", help="LLM provider.")] = "ollama",
    model: Annotated[Optional[str], typer.Option("--model", "-m", help="Model name.")] = None,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: text, json, or markdown"),
    ] = "text",
    dry_run: bool = dry_run_option(),
    no_llm: bool = no_llm_option(),
    verbose: bool = verbose_option(),
    debug: bool = debug_option(),
    discovery_db: Annotated[
        Optional[str],
        typer.Option(
            "--discovery-db",
            help="Path to content discovery SQLite DB.",
            envvar="CONTENT_DISCOVERY_DB_PATH",
        ),
    ] = None,
    voice_memos_dir: Annotated[
        Optional[str],
        typer.Option(
            "--voice-memos-dir",
            help="Directory containing processed voice memo transcriptions.",
            envvar="VOICE_MEMOS_DIR",
        ),
    ] = None,
    days: Annotated[
        Optional[int],
        typer.Option("--days", help="Review the last N days instead of the current calendar week."),
    ] = None,
    month: Annotated[
        bool,
        typer.Option("--month", help="Review the full calendar month containing the target date."),
    ] = False,
    triage_db: Annotated[
        Optional[str],
        typer.Option(
            "--triage-db",
            help="Path to thread-triage SQLite DB. Defaults to ~/sync/thread-triage/thread-triage.db.",
            envvar="THREAD_TRIAGE_DB_PATH",
        ),
    ] = str(Path("~/sync/thread-triage/thread-triage.db").expanduser()),
):
    """Generate a weekly review from Obsidian daily notes."""

    if days is not None and month:
        typer.echo("Error: --days and --month are mutually exclusive.")
        raise typer.Exit(1)

    if no_llm:
        dry_run = True

    target_date = datetime.date.fromisoformat(week) if week else datetime.date.today()

    try:
        llm_provider = resolve_provider(PROVIDERS, provider, model, debug=debug, no_llm=no_llm)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    vault_root = find_vault_root()
    dates = get_date_range(target_date, days=days, month=month)
    period_start = dates[0].isoformat()

    notes = load_daily_notes_for_week(vault_root, dates, subdir="Timeline")
    processed = len(notes)
    skipped = len(dates) - processed

    if not notes:
        typer.echo(f"No notes found for the period starting {period_start} in {vault_root}")
        raise typer.Exit(0)

    # --- Load optional sources ---
    discovery_items = get_kept_items(discovery_db, dates[0], dates[-1]) if discovery_db else None
    voice_memo_texts = get_voice_memos(voice_memos_dir, dates[0], dates[-1]) if voice_memos_dir else None
    triage_capture_items = get_triage_captures(triage_db, dates[0], dates[-1]) if triage_db else None

    notes_text = strip_obsidian_callouts(format_notes_for_llm(notes))
    word_count = get_word_count(notes_text)

    # --- Call LLM ---
    system = get_system_prompt()
    user = get_user_prompt(
        notes_text,
        discovery_items=discovery_items,
        voice_memos=voice_memo_texts,
        triage_captures=triage_capture_items,
    )
    
    try:
        with timed_run("weekly-review-generator", llm_provider.model, source_location=period_start) as run:
            response_data = llm_provider.complete(system=system, user=user, response_model=WeekReview)
            review = process_llm_response(response_data, period_start, word_count)
            run.item_count = processed
            run.input_tokens = getattr(llm_provider, "input_tokens", None) or None
            run.output_tokens = getattr(llm_provider, "output_tokens", None) or None
    except Exception as e:
        typer.echo(f"Error during LLM processing: {e}")
        raise typer.Exit(1)

    # --- Output ---
    review_section = format_review_section(review)
    filename = get_output_filename(target_date, dates, days, month)
    file_path = vault_root / "Timeline" / filename
    template_path = vault_root / "Templates" / "Weekly Note.md"

    if dry_run:
        typer.echo(review_section)
    else:
        file_path.parent.mkdir(exist_ok=True)
        write_review_section(file_path, review_section, template_path=template_path)
        if output != "json":
            typer.echo(f"Wrote review to {file_path}")

    if output == "json":
        typer.echo(review.model_dump_json(indent=2))
    elif output == "markdown":
        typer.echo(format_as_markdown(review))
    elif not dry_run:
        display_week_review(review)

    if output != "json":
        typer.echo(f"\nDone. Processed: {processed}, Skipped: {skipped}")
