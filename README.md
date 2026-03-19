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
```

### 2. Run the Tool

Summarize the current week (Monday to Sunday):

```bash
uv run main.py
```

Summarize a specific week:

```bash
uv run main.py -w 2026-03-02
```

Preview the output without writing to your vault (dry run):

```bash
uv run main.py -n
```

Summarize the last 10 days:

```bash
uv run main.py --days 10
```

Summarize the full current month:

```bash
uv run main.py --month
```

---

## CLI Reference

All tools in this series share a common set of CLI flags for model management.

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--week` | `-w` | today | ISO date in target period. |
| `--days` | | | Review the last N days instead of the current calendar week. |
| `--month` | | | Review the full calendar month containing the target date. |
| `--provider` | `-p` | `ollama` | LLM provider. |
| `--model` | `-m` | provider default | Override the provider's default model. |
| `--output` | `-o` | `text` | Output format: `text`, `json`, or `markdown`. |
| `--dry-run` | `-n` | | Print markdown to stdout instead of writing to vault. |
| `--verbose` | `-v` | | Print info messages and extra context. |
| `--debug` | `-d` | | Show raw system/user prompts and raw LLM responses. |

`--days` and `--month` are mutually exclusive.

---

## Project Structure

This tool follows the [Local-First AI project blueprint](https://github.com/jamalhansen/local-first-common).

```
weekly-review-generator/
├── main.py              # Canonical entry point
├── summarizer.py        # CLI command definitions
├── logic.py             # Core processing logic
├── discovery.py         # Content discovery DB reader
├── voice_memos.py       # Voice memo transcription reader
├── schema.py            # Pydantic models (WeekReview, WeeklyHighlight)
├── prompts.py           # System and user prompt templates
├── display.py           # Rich terminal output
├── markdown_output.py   # Obsidian-compatible markdown formatter
├── pyproject.toml       # Managed by uv
└── tests/
    ├── fixtures/        # Sample daily notes for testing
    ├── test_summarizer.py # CLI tests via MockProvider
    └── ...
```

---

## Running Tests

```bash
uv run pytest
```
