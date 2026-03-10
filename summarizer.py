import datetime
import sys
from typing import Annotated, Optional

import typer

from local_first_common.providers import PROVIDERS
from local_first_common.cli import (
    provider_option,
    model_option,
    dry_run_option,
    verbose_option,
    debug_option,
    resolve_provider,
)
from local_first_common.obsidian import (
    find_vault_root,
    get_week_dates,
    load_daily_notes_for_week,
    format_notes_for_llm,
)
from schema import WeekReview
from prompts import get_system_prompt, get_user_prompt
from display import display_week_review
from markdown_output import format_as_markdown

app = typer.Typer()


def get_word_count(text: str) -> int:
    """Simple word count estimation."""
    return len(text.split())


@app.command()
def summarize(
    week: Annotated[
        Optional[str],
        typer.Option("--week", "-w", help="ISO date in target week (default: current week)"),
    ] = None,
    provider: Annotated[str, provider_option(PROVIDERS)] = "ollama",
    model: Annotated[Optional[str], model_option()] = None,
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output format: text, json, or markdown"),
    ] = "text",
    dry_run: Annotated[bool, dry_run_option()] = False,
    verbose: Annotated[bool, verbose_option()] = False,
    debug: Annotated[bool, debug_option()] = False,
):
    """Summarize a week of Obsidian daily notes using an LLM."""

    # --- Fail fast: validate inputs before doing any work ---

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

    # --- Load notes ---

    dates = get_week_dates(target_date)
    week_start = dates[0].isoformat()

    notes = load_daily_notes_for_week(vault_root, dates, subdir="Timeline")
    processed = len(notes)
    skipped = len(dates) - processed

    if not notes:
        typer.echo(f"No notes found for the week of {week_start} in {vault_root}")
        raise typer.Exit(0)

    if verbose:
        typer.echo(f"\n[Files used for summary]")
        for note in notes:
            typer.echo(f"  {note['path']}")
        typer.echo("")

    notes_text = format_notes_for_llm(notes)
    word_count = get_word_count(notes_text)

    if word_count > 6000:
        typer.echo(f"Warning: Input text is {word_count} words. Large inputs may be truncated or cause errors.")

    # --- Call LLM ---

    try:
        system = get_system_prompt()
        user = get_user_prompt(notes_text)
        response_data = llm_provider.complete(system=system, user=user, response_model=WeekReview)

        if isinstance(response_data, dict):
            response_data["week_of"] = week_start
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

    md_content = format_as_markdown(review)

    timeline_dir = vault_root / "Timeline"
    iso_year, iso_week, _ = target_date.isocalendar()
    filename = f"{iso_year}-W{iso_week:02d}.md"
    file_path = timeline_dir / filename

    if dry_run:
        typer.echo(md_content)
    else:
        timeline_dir.mkdir(exist_ok=True)
        save_confirmed = True
        if file_path.exists():
            response = input(f"File {file_path} already exists. Overwrite? (y/N): ").lower()
            if response != "y":
                save_confirmed = False
                typer.echo("Save cancelled.")

        if save_confirmed:
            try:
                file_path.write_text(md_content)
                typer.echo(f"Saved review to {file_path}")
            except Exception as e:
                typer.echo(f"Error: Failed to save to {file_path}: {e}")

    if output == "json":
        typer.echo(review.model_dump_json(indent=2))
    elif output == "markdown":
        typer.echo(md_content)
    elif not dry_run:
        display_week_review(review)

    typer.echo(f"\nDone. Processed: {processed}, Skipped: {skipped}")


if __name__ == "__main__":
    app()
