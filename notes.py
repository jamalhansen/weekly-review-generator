import os
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import frontmatter

def find_vault_root() -> Path:
    """Find the Obsidian vault root via OBSIDIAN_VAULT_PATH or by looking for .obsidian/."""
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if vault_path:
        return Path(vault_path)
    
    # Walk up from current directory looking for .obsidian
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".obsidian").is_dir():
            return parent
            
    # Default to current directory if not found (might be testing)
    return current

def get_week_dates(date_in_week: datetime.date) -> List[datetime.date]:
    """Get the 7 dates (Mon-Sun) for the week containing date_in_week."""
    # weekday() is 0 for Monday, 6 for Sunday
    monday = date_in_week - datetime.timedelta(days=date_in_week.weekday())
    return [monday + datetime.timedelta(days=i) for i in range(7)]

def load_notes_for_week(vault_root: Path, dates: List[datetime.date]) -> List[Dict[str, Any]]:
    """Load and parse daily notes for the given dates. Returns list of {date, content, path}."""
    notes = []
    timeline_path = vault_root / "Timeline"
    
    if not timeline_path.is_dir():
        # Fallback to vault root if Timeline doesn't exist (helpful for testing)
        timeline_path = vault_root

    for date in dates:
        file_path = timeline_path / f"{date.isoformat()}.md"
        if file_path.is_file():
            try:
                post = frontmatter.load(file_path)
                notes.append({
                    "date": date,
                    "content": post.content,
                    "path": file_path
                })
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")
                
    return notes

def format_notes_for_llm(notes: List[Dict[str, Any]]) -> str:
    """Combine notes into a single string for the LLM."""
    output = []
        
    for note in notes:
        output.append(f"## DATE: {note['date'].isoformat()}")
        output.append(note['content'])
        output.append("\n---\n")
        
    return "\n".join(output)

def get_word_count(text: str) -> int:
    """Simple word count estimation."""
    return len(text.split())
