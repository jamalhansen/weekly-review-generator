import calendar
import datetime
import os
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

from local_first_common.providers import PROVIDERS
from local_first_common.cli import resolve_provider
from local_first_common.obsidian import (
    find_vault_root,
    get_week_dates,
    load_daily_notes_for_week,
    format_notes_for_llm,
)
from schema import WeekReview
from prompts import get_system_prompt, get_user_prompt
from display import display_week_review
from markdown_output import format_as_markdown, format_review_section, write_review_section
from discovery import get_kept_items
from triage import get_triage_captures
from voice_memos import get_voice_memos

app = typer.Typer()


def strip_obsidian_callouts(text: str) -> str:
    """Convert Obsidian callout blocks to plain prose for LLM consumption.

    Callout blocks wrap content in `> ` prefixes, which causes LLMs to treat
    the content as lower-priority blockquotes. This is especially problematic
    for Morning Pages, which contain the richest daily content.

    Transforms:
        > [!pencil]- Click to expand...
        >
        > Actual content here.
    Into:
        Actual content here.
    """
    lines = text.splitlines()
    result = []
    for line in lines:
        # Drop callout opener lines: "> [!type]- ..." or "> [!type]+ ..."
        if re.match(r"^>\s*\[!", line):
            continue
        # Strip leading "> " or ">" from blockquote continuation lines
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


@app.command()
def summarize(
    week: Annotated[
        Optional[str],
        typer.Option("--week", "-w", help="ISO date in target period (default: today)"),
    ] = None,
    provider: Annotated[
        str,
        typer.Option("--provider", "-p", help=f"LLM provider. Choices: {', '.join(PROVIDERS.keys())}"),
    ] = os.environ.get("MODEL_PROVIDER", "ollama"),
    model: Annotated[
        Optional[str],
        typer.Option("--model", "-m", help="Override the provider's default model."),
    ] = None,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: text, json, or markdown"),
    ] = "text",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Preview output without writing files or calling LLM."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show extra debug output."),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", "-d", help="Show raw prompts and LLM responses."),
    ] = False,
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
    """Generate a weekly review from Obsidian daily notes (and optionally voice memos and content discovery)."""

    # --- Fail fast: validate inputs before doing any work ---

    if days is not None and month:
        typer.echo("Error: --days and --month are mutually exclusive.")
        raise typer.Exit(1)

    if days is not None and days < 1:
        typer.echo("Error: --days must be a positive integer.")
        raise typer.Exit(1)

    if week:
        try:
            target_date = datetime.date.fromisoformat(week)
        except ValueError:
            typer.echo(f"Error: Invalid date format '{week}'. Use YYYY-MM-DD.")
            raise typer.Exit(1)
    else:
        target_date = datetime.date.today()

    try:
        llm_provider = resolve_provider(PROVIDERS, provider, model, debug=debug)
    except typer.BadParameter as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    except RuntimeError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    vault_root = find_vault_root()

    # --- Compute date range ---

    dates = get_date_range(target_date, days=days, month=month)
    period_start = dates[0].isoformat()

    # --- Load daily notes ---

    notes = load_daily_notes_for_week(vault_root, dates, subdir="Timeline")
    processed = len(notes)
    skipped = len(dates) - processed

    if not notes:
        typer.echo(f"No notes found for the period starting {period_start} in {vault_root}")
        raise typer.Exit(0)

    if verbose:
        typer.echo("\n[Files used for summary]")
        for note in notes:
            typer.echo(f"  {note['path']}")

    # --- Load optional sources ---

    discovery_items = None
    if discovery_db:
        try:
            discovery_items = get_kept_items(discovery_db, dates[0], dates[-1])
            if verbose:
                typer.echo(f"\n[Content discovery] {len(discovery_items)} kept items from {discovery_db}")
        except RuntimeError as e:
            typer.echo(f"Warning: {e}. Proceeding without content discovery.")
            discovery_items = None

    voice_memo_texts = None
    if voice_memos_dir:
        voice_memo_texts = get_voice_memos(voice_memos_dir, dates[0], dates[-1])
        if verbose:
            typer.echo(f"[Voice memos] {len(voice_memo_texts)} memo(s) from {voice_memos_dir}")
        if not voice_memo_texts:
            voice_memo_texts = None

    triage_capture_items = None
    if triage_db:
        try:
            triage_capture_items = get_triage_captures(triage_db, dates[0], dates[-1])
            if verbose:
                typer.echo(f"[Triage captures] {len(triage_capture_items)} capture(s) from {triage_db}")
            if not triage_capture_items:
                triage_capture_items = None
        except RuntimeError as e:
            typer.echo(f"Warning: {e}. Proceeding without triage captures.")
            triage_capture_items = None

    if verbose:
        typer.echo("")

    notes_text = strip_obsidian_callouts(format_notes_for_llm(notes))
    word_count = get_word_count(notes_text)

    if word_count > 6000:
        typer.echo(f"Warning: Input text is {word_count} words. Large inputs may be truncated or cause errors.")

    # --- Call LLM ---

    try:
        system = get_system_prompt()
        user = get_user_prompt(
            notes_text,
            discovery_items=discovery_items,
            voice_memos=voice_memo_texts,
            triage_captures=triage_capture_items,
        )
        response_data = llm_provider.complete(system=system, user=user, response_model=WeekReview)

        if isinstance(response_data, dict):
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

            review = WeekReview(**response_data)
        else:
            typer.echo("Error: Unexpected response format from LLM.")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Error during LLM processing: {e}")
        raise typer.Exit(1)

    # --- Output ---

    review_section = format_review_section(review)

    timeline_dir = vault_root / "Timeline"
    filename = get_output_filename(target_date, dates, days, month)
    file_path = timeline_dir / filename
    template_path = vault_root / "Templates" / "Weekly Note.md"

    if dry_run:
        typer.echo(review_section)
    else:
        timeline_dir.mkdir(exist_ok=True)
        try:
            write_review_section(file_path, review_section, template_path=template_path)
            typer.echo(f"Wrote review to {file_path} (## Review section)")
        except Exception as e:
            typer.echo(f"Error: Failed to write to {file_path}: {e}")

    if output == "json":
        typer.echo(review.model_dump_json(indent=2))
    elif output == "markdown":
        typer.echo(format_as_markdown(review))
    elif not dry_run:
        display_week_review(review)

    typer.echo(f"\nDone. Processed: {processed}, Skipped: {skipped}")


if __name__ == "__main__":
    app()
