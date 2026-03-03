# Daily Note Summarizer

Tool #4 in the `local-ai-tools` series. Reads a week of Obsidian daily notes and generates a structured "Week in Review" summary.

---

## Features

- **Automated Summarization:** Extracts headlines, highlights, and links.
- **Open Thread Discovery:** Surfaces unchecked tasks and unresolved questions.
- **Obsidian Integration:** Saves directly to your `Timeline/` folder in `YYYY-Www.md` format.
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

By default the review is written to `Timeline/YYYY-Www.md` in your vault.

Use a specific provider and model:

```bash
uv run python summarizer.py -p anthropic -m claude-sonnet-4-6
```

---

## CLI Reference

| Flag | Short | Options | Description |
|------|-------|---------|-------------|
| `--week` | `-w` | `YYYY-MM-DD` | Summarizes the week containing this date (default: today). |
| `--provider` | `-p` | `ollama`, `anthropic`, `gemini`, `groq`, `deepseek` | LLM provider (default: `ollama`). |
| `--model` | `-m` | string | Override the provider's default model. |
| `--output` | `-o` | `text`, `json`, `markdown` | Output format (default: `text`). |
| `--dry-run` | `-n` | flag | Print markdown to stdout instead of writing to vault. |
| `--verbose` | `-v` | flag | Show which files are being summarized. |
| `--debug` | `-d` | flag | Show raw LLM prompt and response. |

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

## Project Structure

```
daily-note-summarizer/
├── summarizer.py        # CLI entrypoint
├── notes.py             # Vault discovery and note loading
├── schema.py            # Pydantic models (WeekReview, WeeklyHighlight)
├── prompts.py           # System and user prompt templates
├── display.py           # Rich terminal output
├── markdown_output.py   # Obsidian-compatible markdown formatter
├── providers/           # LLM provider abstraction
│   ├── __init__.py      # PROVIDERS dict
│   ├── base.py          # Abstract BaseProvider
│   ├── ollama.py
│   ├── anthropic.py
│   ├── gemini.py
│   ├── groq.py
│   └── deepseek.py
├── tests/
│   ├── fixtures/        # Sample daily notes for testing
│   ├── test_notes.py
│   ├── test_schema.py
│   ├── test_markdown_output.py
│   └── test_providers.py
└── pyproject.toml
```

---

## Running Tests

```bash
uv run pytest
```
