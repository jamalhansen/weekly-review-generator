from datetime import date
from pathlib import Path

import frontmatter


def get_voice_memos(dir_path: str, start_date: date, end_date: date) -> list[str]:
    """Return journal-entry text for voice memos in the given date range.

    Looks for .md and .txt files whose names start with YYYY-MM-DD in dir_path.
    Returns an empty list if the directory doesn't exist or has no matching files.
    This is a graceful no-op — callers should treat an empty result as "no memos".

    Each voice-journal memo note carries YAML frontmatter (date, time, type,
    source_audio) ahead of its entry text -- strip it via `frontmatter.load` (the
    same library `local_first_common.obsidian` uses for daily notes) so the LLM
    prompt gets the entry itself, not raw file bytes with a metadata block glued
    to the front. A plain .txt file with no frontmatter round-trips unchanged.
    """
    p = Path(dir_path)
    if not p.exists() or not p.is_dir():
        return []

    memos = []
    for filepath in sorted(p.iterdir()):
        if filepath.suffix not in (".md", ".txt"):
            continue
        try:
            file_date = date.fromisoformat(filepath.stem[:10])
        except ValueError:
            continue
        if start_date <= file_date <= end_date:
            post = frontmatter.load(str(filepath))
            memos.append(post.content.strip())

    return memos
