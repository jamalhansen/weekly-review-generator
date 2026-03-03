import argparse
import datetime
import json
import sys
from pathlib import Path

from client import ModelClient
from notes import (
    find_vault_root, 
    get_week_dates, 
    load_notes_for_week, 
    format_notes_for_llm,
    get_word_count
)
from schema import WeekReview
from prompts import get_system_prompt, get_user_prompt
from display import display_week_review
from markdown_output import format_as_markdown

def main():
    parser = argparse.ArgumentParser(description="Summarize a week of Obsidian daily notes.")
    parser.add_argument("--week", type=str, help="Date in the target week (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--backend", type=str, choices=["ollama", "anthropic", "gemini", "groq", "deepseek"], help="LLM backend to use.")
    parser.add_argument("--model", type=str, help="Model name to use.")
    parser.add_argument("--output", type=str, choices=["text", "json", "markdown"], default="text", help="Output format.")
    parser.add_argument("--save", action="store_true", help="Save the markdown output to the vault Timeline folder.")
    parser.add_argument("--verbose", action="store_true", help="Show the files being used for the summary.")
    parser.add_argument("--debug", action="store_true", help="Show raw LLM input and output.")
    
    args = parser.parse_args()
    
    # 1. Determine target date and week dates
    if args.week:
        try:
            target_date = datetime.date.fromisoformat(args.week)
        except ValueError:
            print(f"Error: Invalid date format: {args.week}. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = datetime.date.today()
        
    dates = get_week_dates(target_date)
    week_start = dates[0].isoformat()
    
    # 2. Find vault and load notes
    vault_root = find_vault_root()
    notes = load_notes_for_week(vault_root, dates)
    
    if not notes:
        print(f"No notes found for the week of {week_start} in {vault_root}")
        sys.exit(0)
        
    if args.verbose:
        print(f"\n[Files used for summary]")
        for note in notes:
            print(f"Note:  {note['path']}")
        print("")

    notes_text = format_notes_for_llm(notes)
    word_count = get_word_count(notes_text)
    
    # Check for long input fallback (warning for now)
    if word_count > 6000:
        print(f"Warning: Input text is {word_count} words. Large inputs may be truncated or cause errors.")
        
    # 3. Initialize client and request summary
    try:
        client = ModelClient(backend=args.backend, model=args.model, debug=args.debug)
        
        system = get_system_prompt()
        user = get_user_prompt(notes_text)
        
        response_data = client.complete(system=system, user=user, response_model=WeekReview)
        
        # Ensure week_of is set correctly and group highlights if needed
        if isinstance(response_data, dict):
            response_data["week_of"] = week_start
            response_data["word_count_input"] = word_count
            
            # Post-process: Group highlights by category
            raw_highlights = response_data.get("highlights", [])
            if raw_highlights:
                grouped = {}
                for h in raw_highlights:
                    cat = h.get("category", "Other")
                    if cat not in grouped:
                        grouped[cat] = {"category": cat, "summary": h.get("summary", ""), "items": h.get("items", []) or []}
                    else:
                        # Append summary and items
                        if h.get("summary"):
                            grouped[cat]["summary"] += " " + h["summary"]
                        if h.get("items"):
                            grouped[cat]["items"].extend(h["items"])
                response_data["highlights"] = list(grouped.values())
                
            review = WeekReview(**response_data)
        else:
            print(f"Error: Unexpected response format from LLM.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error during LLM processing: {e}")
        sys.exit(1)
        
    # 4. Output and Save logic
    md_content = format_as_markdown(review)
    
    if args.save:
        timeline_dir = vault_root / "Timeline"
        timeline_dir.mkdir(exist_ok=True)
        
        iso_year, iso_week, _ = target_date.isocalendar()
        filename = f"{iso_year}-W{iso_week:02d}.md"
        file_path = timeline_dir / filename
        
        save_confirmed = True
        if file_path.exists():
            response = input(f"File {file_path} already exists. Overwrite? (y/N): ").lower()
            if response != 'y':
                save_confirmed = False
                print("Save cancelled.")
        
        if save_confirmed:
            try:
                with open(file_path, "w") as f:
                    f.write(md_content)
                print(f"Successfully saved review to {file_path}")
            except Exception as e:
                print(f"Error: Failed to save to {file_path}: {e}")

    if args.output == "json":
        print(review.model_dump_json(indent=2))
    elif args.output == "markdown":
        print(md_content)
    else:
        display_week_review(review)

if __name__ == "__main__":
    main()
