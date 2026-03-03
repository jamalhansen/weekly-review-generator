import argparse
import datetime
import json
import os
import sys
from pathlib import Path

from notes import (
    find_vault_root,
    get_week_dates,
    load_notes_for_week,
    format_notes_for_llm,
    get_word_count,
)
from providers import PROVIDERS
from schema import WeekReview
from prompts import get_system_prompt, get_user_prompt
from display import display_week_review
from markdown_output import format_as_markdown


def main():
    parser = argparse.ArgumentParser(description="Summarize a week of Obsidian daily notes.")
    parser.add_argument("--week", "-w", type=str, help="Date in the target week (YYYY-MM-DD). Defaults to today.")
    parser.add_argument(
        "--provider", "-p",
        type=str,
        choices=list(PROVIDERS.keys()),
        default=os.environ.get("MODEL_PROVIDER", "ollama"),
        help="LLM provider to use (default: ollama).",
    )
    parser.add_argument("--model", "-m", type=str, help="Override the provider's default model.")
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument("--dry-run", "-n", action="store_true", help="Print the markdown to stdout instead of writing to the vault.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show the files being used for the summary.")
    parser.add_argument("--debug", "-d", action="store_true", help="Show raw LLM input and output.")

    args = parser.parse_args()

    # --- Fail fast: validate inputs before doing any work ---

    if args.week:
        try:
            target_date = datetime.date.fromisoformat(args.week)
        except ValueError:
            print(f"Error: Invalid date format '{args.week}'. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = datetime.date.today()

    try:
        provider = PROVIDERS[args.provider](model=args.model, debug=args.debug)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    vault_root = find_vault_root()

    # --- Load notes ---

    dates = get_week_dates(target_date)
    week_start = dates[0].isoformat()

    notes = load_notes_for_week(vault_root, dates)
    processed = len(notes)
    skipped = len(dates) - processed

    if not notes:
        print(f"No notes found for the week of {week_start} in {vault_root}")
        sys.exit(0)

    if args.verbose:
        print(f"\n[Files used for summary]")
        for note in notes:
            print(f"  {note['path']}")
        print()

    notes_text = format_notes_for_llm(notes)
    word_count = get_word_count(notes_text)

    if word_count > 6000:
        print(f"Warning: Input text is {word_count} words. Large inputs may be truncated or cause errors.")

    # --- Call LLM ---

    try:
        system = get_system_prompt()
        user = get_user_prompt(notes_text)
        response_data = provider.complete(system=system, user=user, response_model=WeekReview)

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
            print("Error: Unexpected response format from LLM.")
            sys.exit(1)

    except Exception as e:
        print(f"Error during LLM processing: {e}")
        sys.exit(1)

    # --- Output ---

    md_content = format_as_markdown(review)

    timeline_dir = vault_root / "Timeline"
    iso_year, iso_week, _ = target_date.isocalendar()
    filename = f"{iso_year}-W{iso_week:02d}.md"
    file_path = timeline_dir / filename

    if args.dry_run:
        print(md_content)
    else:
        timeline_dir.mkdir(exist_ok=True)
        save_confirmed = True
        if file_path.exists():
            response = input(f"File {file_path} already exists. Overwrite? (y/N): ").lower()
            if response != "y":
                save_confirmed = False
                print("Save cancelled.")

        if save_confirmed:
            try:
                file_path.write_text(md_content)
                print(f"Saved review to {file_path}")
            except Exception as e:
                print(f"Error: Failed to save to {file_path}: {e}")

    if args.output == "json":
        print(review.model_dump_json(indent=2))
    elif args.output == "markdown":
        print(md_content)
    elif not args.dry_run:
        display_week_review(review)

    print(f"\nDone. Processed: {processed}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
