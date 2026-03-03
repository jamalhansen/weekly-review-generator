# Daily Note Summarizer

Tool #4 in the `local-ai-tools` series. Reads a week of Obsidian daily notes and generates a structured "Week in Review" summary.

---

## Features

- **Automated Summarization:** Extracts headlines, highlights, and links.
- **Open Thread Discovery:** Surfaces unchecked tasks and unresolved questions.
- **Obsidian Integration:** Saves directly to your `Timeline/` folder in `YYYY-Www.md` format.
- **Multiple Backends:** Supports Ollama (default), Anthropic, Gemini, Groq, and DeepSeek.
- **Structured Output:** Pydantic-validated JSON, human-readable terminal text, or Obsidian-compatible Markdown.

---

## Quick Start

### 1. Set Up Your Environment

You must have **uv** installed and your Obsidian vault path configured.

```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/obsidian/vault"

# If using cloud backends:
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
uv run python summarizer.py --week 2026-03-02
```

Save the review directly into your Obsidian `Timeline/` folder:

```bash
uv run python summarizer.py --save
```

---

## Usage

| Argument | Options | Description |
| --- | --- | --- |
| `--week` | `YYYY-MM-DD` | Summarizes the week containing this date (default: today). |
| `--backend` | `ollama`, `anthropic`, `gemini`, `groq`, `deepseek` | Choose your LLM backend (default: `ollama`). |
| `--model` | `string` | Override the default model for the chosen backend. |
| `--output` | `text`, `json`, `markdown` | Set the output format (default: `text`). |
| `--save` | (flag) | Saves to `Timeline/YYYY-Www.md` in your vault (asks before overwrite). |
| `--verbose` | (flag) | Shows the files being used for the summary. |

---

## Technical Details

- **Default Models:** 
  - Ollama: `phi4-mini`
  - Anthropic: `claude-3-haiku-20240307`
  - Gemini: `gemini-1.5-flash`
  - Groq: `llama-3.3-70b-versatile`
  - DeepSeek: `deepseek-chat`
- **Input Limit:** If your notes exceed ~6000 words, a warning will be issued.
- **Dependencies:** Managed via `pyproject.toml` and `uv.lock`.
