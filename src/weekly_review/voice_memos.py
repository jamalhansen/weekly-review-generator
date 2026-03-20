from datetime import date
from pathlib import Path


def get_voice_memos(dir_path: str, start_date: date, end_date: date) -> list[str]:
    """Return transcription text for voice memos in the given date range.

    Looks for .md and .txt files whose names start with YYYY-MM-DD in dir_path.
    Returns an empty list if the directory doesn't exist or has no matching files.
    This is a graceful no-op — callers should treat an empty result as "no memos".
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
            memos.append(filepath.read_text())

    return memos
