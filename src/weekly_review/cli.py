import datetime
import logging
import os
from pathlib import Path
from typing import Annotated

import typer
from local_first_common.cli import (
    debug_option,
    dry_run_option,
    init_config_option,
    model_option,
    no_llm_option,
    provider_option,
    resolve_dry_run,
    resolve_provider,
    verbose_option,
)
from local_first_common.logging import setup_logging
from local_first_common.obsidian import (
    find_vault_root,
    format_notes_for_llm,
    load_daily_notes_for_week,
)
from local_first_common.providers import PROVIDERS
from local_first_common.tracking import register_tool, timed_run

from .core import (
    LLMRunError,
    ProviderSetupError,
    get_date_range,
    get_output_filename,
    get_word_count,
    process_llm_response,
    strip_obsidian_callouts,
)
from .discovery import get_kept_items
from .display import display_week_review
from .markdown_output import (
    format_as_markdown,
    format_review_section,
    write_review_section,
)
from .prompts import get_system_prompt, get_user_prompt
from .schema import WeekReview
from .triage import get_triage_captures
from .voice_memos import get_voice_memos

_TOOL = register_tool("weekly-review-generator")
TOOL_NAME = "weekly-review-generator"
DEFAULTS = {"provider": "ollama", "model": "llama3"}

app = typer.Typer()


def _setup_tool_logging(verbose: bool, debug: bool) -> None:
    level = logging.DEBUG if (verbose or debug) else logging.WARNING
    try:
        setup_logging(
            level=level,
            tool_name=TOOL_NAME,
            persist_warnings=True,
        )
    except TypeError:
        # Backward compatibility with older local-first-common logging signature.
        setup_logging(level=level)


@app.command()
def summarize(
    week: str | None = typer.Option(
        None, "--week", "-w", help="ISO date in target period (default: today)"
    ),
    provider: Annotated[str, provider_option()] = os.environ.get(
        "MODEL_PROVIDER", "ollama"
    ),
    model: Annotated[str | None, model_option()] = None,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: text, json, or markdown"),
    ] = "text",
    dry_run: Annotated[bool, dry_run_option()] = False,
    no_llm: Annotated[bool, no_llm_option()] = False,
    verbose: Annotated[bool, verbose_option()] = False,
    debug: Annotated[bool, debug_option()] = False,
    init_config: Annotated[bool, init_config_option(TOOL_NAME, DEFAULTS)] = False,
    discovery_db: str | None = typer.Option(
        None,
        "--discovery-db",
        help="Path to content discovery SQLite DB.",
        envvar="CONTENT_DISCOVERY_DB_PATH",
    ),
    voice_memos_dir: str | None = typer.Option(
        None,
        "--voice-memos-dir",
        help="Directory containing processed voice memo transcriptions.",
        envvar="VOICE_MEMOS_DIR",
    ),
    days: int | None = typer.Option(
        None,
        "--days",
        help="Review the last N days instead of the current calendar week.",
    ),
    month: bool = typer.Option(
        False,
        "--month",
        help="Review the full calendar month containing the target date.",
    ),
    triage_db: str | None = typer.Option(
        str(Path("~/sync/thread-triage/thread-triage.db").expanduser()),
        "--triage-db",
        help="Path to thread-triage SQLite DB. Defaults to ~/sync/thread-triage/thread-triage.db.",
        envvar="THREAD_TRIAGE_DB_PATH",
    ),
):
    """Generate a weekly review from Obsidian daily notes."""
    _setup_tool_logging(verbose, debug)

    if days is not None and month:
        typer.echo("Error: --days and --month are mutually exclusive.")
        raise typer.Exit(1)

    dry_run = resolve_dry_run(dry_run, no_llm)

    target_date = (
        datetime.date.fromisoformat(week)
        if week
        else datetime.datetime.now().astimezone().date()
    )

    try:
        llm_provider = resolve_provider(
            PROVIDERS, provider, model, debug=debug, no_llm=no_llm
        )
    except ProviderSetupError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)
    except Exception as e:  # noqa: BLE001 - top-level CLI boundary: report cleanly and exit, don't show a raw traceback
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

    vault_root = find_vault_root()
    dates = get_date_range(target_date, days=days, month=month)
    period_start = dates[0].isoformat()

    notes = load_daily_notes_for_week(vault_root, dates, subdir="Timeline")
    processed = len(notes)
    skipped = len(dates) - processed

    if not notes:
        typer.echo(
            f"No notes found for the period starting {period_start} in {vault_root}"
        )
        raise typer.Exit(0)

    # --- Load optional sources ---
    discovery_items = (
        get_kept_items(discovery_db, dates[0], dates[-1]) if discovery_db else None
    )
    voice_memo_texts = (
        get_voice_memos(voice_memos_dir, dates[0], dates[-1])
        if voice_memos_dir
        else None
    )
    triage_capture_items = (
        get_triage_captures(triage_db, dates[0], dates[-1]) if triage_db else None
    )

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
        with timed_run(
            "weekly-review-generator", llm_provider.model, source_location=period_start
        ) as run:
            response_data = llm_provider.complete(
                system=system, user=user, response_model=WeekReview
            )
            review = process_llm_response(response_data, period_start, word_count)
            run.item_count = processed
            run.input_tokens = getattr(llm_provider, "input_tokens", None) or None
            run.output_tokens = getattr(llm_provider, "output_tokens", None) or None
    except LLMRunError as e:
        typer.echo(f"Error during LLM processing: {e}")
        raise typer.Exit(1)
    except Exception as e:  # noqa: BLE001 - top-level CLI boundary: report cleanly and exit, don't show a raw traceback
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


if __name__ == "__main__":
    app()
