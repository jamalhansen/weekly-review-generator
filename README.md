# Weekly Review Generator

Tool #4 in the `local-ai-tools` series. Reads a period of Obsidian daily notes (and optionally voice memo transcriptions and content discovery items) and generates a structured "Week in Review" summary.

---

## Features

- **Multi-Source Synthesis:** Combines daily notes, voice memos, and content discovery into one review.
- **Automated Summarization:** Extracts headlines, highlights, and links.
- **Open Thread Discovery:** Surfaces unchecked tasks and unresolved questions.
- **Obsidian Integration:** Saves directly to your `Timeline/` folder.
- **Flexible Date Ranges:** Summarize the current week, last N days, or the full month.
- **Multiple Providers:** Supports Ollama (default), Anthropic, Gemini, Groq, and DeepSeek.
- **Structured Output:** Pydantic-validated JSON, human-readable terminal text, or Obsidian-compatible Markdown.

---

## Quick Start

### 1. Set Up Your Environment

You must have **uv** installed and your Obsidian vault path configured.

```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/obsidian/vault"

# If using cloud providers:
export ANTHROPIC_API_KEY="your-key"
export GEMINI_API_KEY="your-key"
export GROQ_API_KEY="your-key"
export DEEPSEEK_API_KEY="your-key"

# Optional — Phase 2 sources:
export CONTENT_DISCOVERY_DB_PATH="$HOME/.content-discovery.db"
export VOICE_MEMOS_DIR="$HOME/voice-memos/transcriptions"
```

### 2. Run the Tool

Summarize the current week (Monday to Sunday):

```bash
uv run python summarizer.py
```

Summarize a specific week:

```bash
uv run python summarizer.py -w 2026-03-02
```

Preview the output without writing to your vault (dry run):

```bash
uv run python summarizer.py -n
```

Summarize the last 10 days:

```bash
uv run python summarizer.py --days 10
```

Summarize the full current month:

```bash
uv run python summarizer.py --month
```

Include content discovery and voice memos:

```bash
uv run python summarizer.py \
  --discovery-db ~/.content-discovery.db \
  --voice-memos-dir ~/voice-memos/transcriptions
```

Use a specific provider and model:

```bash
uv run python summarizer.py -p anthropic -m claude-sonnet-4-6
```

By default the review is written to `Timeline/YYYY-Www.md` in your vault. With `--days`, it writes to `Timeline/YYYY-MM-DD--YYYY-MM-DD.md`. With `--month`, it writes to `Timeline/YYYY-MM.md`.

---

## CLI Reference

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--week` | `-w` | today | ISO date in target period. |
| `--days` | | | Review the last N days instead of the current calendar week. |
| `--month` | | | Review the full calendar month containing the target date. |
| `--provider` | `-p` | `ollama` | LLM provider. |
| `--model` | `-m` | provider default | Override the provider's default model. |
| `--output` | `-o` | `text` | Output format: `text`, `json`, or `markdown`. |
| `--dry-run` | `-n` | | Print markdown to stdout instead of writing to vault. |
| `--verbose` | `-v` | | Show which files are being summarized and source counts. |
| `--debug` | `-d` | | Show raw LLM prompt and response. |
| `--discovery-db` | | `$CONTENT_DISCOVERY_DB_PATH` | Path to content discovery SQLite DB. |
| `--voice-memos-dir` | | `$VOICE_MEMOS_DIR` | Directory of processed voice memo transcriptions. |

`--days` and `--month` are mutually exclusive.

---

## Provider Details

| Provider | Default Model | Env Var |
|----------|--------------|---------|
| `ollama` | `phi4-mini` | *(none — local)* |
| `anthropic` | `claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |
| `gemini` | `gemini-2.0-flash` | `GEMINI_API_KEY` |
| `groq` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| `deepseek` | `deepseek-chat` | `DEEPSEEK_API_KEY` |

You can also set `MODEL_PROVIDER` as an environment variable to change the default provider without passing `-p` every time.

---

## Content Discovery Integration (Phase 2)

When `--discovery-db` is provided (or `CONTENT_DISCOVERY_DB_PATH` is set), the tool queries for items with `status = 'kept'` in the review period:

```sql
SELECT title, url, summary, tags, score FROM items
WHERE status = 'kept' AND fetched_at BETWEEN ? AND ?
ORDER BY score DESC
```

The source DB is read-only — no writes, no schema changes.

## Voice Memo Integration (Phase 2)

When `--voice-memos-dir` is provided (or `VOICE_MEMOS_DIR` is set), the tool reads `.md` and `.txt` files whose names start with `YYYY-MM-DD`. Files are matched to the review period by date prefix. If the directory doesn't exist or has no matching files, the tool proceeds without memos.

---

## Project Structure

```
weekly-review-generator/
├── summarizer.py        # CLI entrypoint
├── discovery.py         # Content discovery DB reader
├── voice_memos.py       # Voice memo transcription reader
├── schema.py            # Pydantic models (WeekReview, WeeklyHighlight)
├── prompts.py           # System and user prompt templates
├── display.py           # Rich terminal output
├── markdown_output.py   # Obsidian-compatible markdown formatter
├── tests/
│   ├── fixtures/        # Sample daily notes for testing
│   ├── test_notes.py
│   ├── test_schema.py
│   ├── test_markdown_output.py
│   ├── test_providers.py
│   ├── test_discovery.py
│   └── test_voice_memos.py
└── pyproject.toml
```

---

## Running Tests

```bash
uv run pytest
```
