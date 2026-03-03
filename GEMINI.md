# Daily Note Summarizer

Tool #4 in the `local-ai-tools` series. Reads a week of Obsidian daily notes and generates a structured "Week in Review" summary: what was worked on, links saved, decisions made, and progress toward monthly goals.

Part of the **Local-First AI: Small Models, Sharp Tools** blog series (Post 7: The Summarizer in Your Pocket).

---

## Run It

```bash
python summarizer.py                          # summarizes current week (Mon-Sun)
python summarizer.py --week 2026-03-02        # week containing this date
python summarizer.py --backend anthropic      # swap to Haiku
python summarizer.py --output json            # raw JSON
python summarizer.py --output text            # human-readable (default)
```

---

## Tech Stack

- **Python 3.11+**
- **Ollama** (default backend) -- model: `phi4-mini` or `llama3.2:3b`
- **Anthropic Python SDK** (optional backend)
- **Pydantic** -- output schema
- **Rich** -- terminal output in text mode
- **python-frontmatter** -- parse daily note markdown + YAML
- **pathlib** -- vault file traversal

No frameworks. Direct API calls through the shared ModelClient from Tool #1.

---

## Project Structure

```
daily-note-summarizer/
├── GEMINI.md               # this file
├── README.md
├── summarizer.py           # CLI entry point
├── client.py               # ModelClient (import or copy from Tool #1)
├── notes.py                # daily note discovery and parsing
├── schema.py               # Pydantic output models
├── prompts.py              # system and user prompt builders
├── display.py              # Rich formatting
├── requirements.txt
└── examples/
    └── sample-week/        # a week of test daily notes
```

---

## Vault Layout (What the Tool Reads)

Daily notes live in `Timeline/` at the vault root. Filenames follow `YYYY-MM-DD.md`. Each note may contain:

- A `## Gratitude` section
- A `## Thoughts` section (freeform)
- Checkboxes (`- [ ]` / `- [x]`) with optional tags (`#writing`, `#localai`, etc.)
- Wikilinks to other notes (`[[some-note]]`)
- External URLs

The tool discovers the vault root via `OBSIDIAN_VAULT_PATH` env var. If not set, look for a `.obsidian/` directory walking up from the current directory.

---

## Output Schema

```python
class WeeklyHighlight(BaseModel):
    category: str        # "Work", "Learning", "Writing", "Personal", "Links"
    summary: str         # 1-2 sentences
    items: list[str]     # specific bullet points

class GoalProgress(BaseModel):
    goal: str
    status: str          # brief assessment
    evidence: str        # what in the notes supports this

class WeekReview(BaseModel):
    week_of: str                      # "2026-03-02"
    headline: str                     # one sentence capturing the week
    highlights: list[WeeklyHighlight]
    goal_progress: list[GoalProgress]
    links_saved: list[str]            # URLs found in the notes
    open_threads: list[str]           # unresolved items, incomplete tasks, loose thoughts
    word_count_input: int             # total words fed to the model
```

---

## Design Decisions

### Single-shot

One LLM call. All seven notes concatenated with clear date headers, sent as the user prompt. System prompt defines the output schema and extraction rules. No iteration, no tool calls.

If total input exceeds ~6000 words, summarize each day individually first (one call per note), then do a second call to synthesize the daily summaries. Log a warning when this fallback triggers. Most weeks won't hit this.

### Summarization, not generation

The model is extracting and condensing -- not inventing. System prompt makes this explicit: "Only report what appears in the notes. Do not infer or embellish." This constraint helps smaller models perform reliably.

### Structured output, always

Output is always a validated Pydantic model, even in text mode. The display layer formats it for humans; the underlying data is always structured. This matters because this tool is a natural input for Tool #10 (Goal Progress Tracker), which will consume `goal_progress` directly.

### ModelClient is shared

`client.py` is the same abstraction used in Tool #1 (Blog Draft Reviewer). Either copy it into this project or factor it out into a shared `local_ai_tools` package. The interface is:

```python
client = ModelClient(backend="ollama", model="phi4-mini")
response = client.complete(system=SYSTEM_PROMPT, user=notes_text)
```

Backend swappable via `--backend` flag or `MODEL_BACKEND` env var.

### Scheduled use is the primary use case

This tool is most valuable running automatically. The README should include a cron example:

```
0 8 * * 1  cd /path/to/tool && python summarizer.py >> ~/weekly-reviews.log 2>&1
```

Manual invocation is also supported (for catching up on a past week, or running mid-week). Design for scheduled first; manual is a flag away.

### Goal progress is opt-in

If the monthly goals file can be found (via `OBSIDIAN_VAULT_PATH`), the tool reads it and tries to match evidence from the week's notes to each goal. If the file is not found, `goal_progress` is an empty list and no error is raised. Degrade gracefully.

Monthly goals file path: `{OBSIDIAN_VAULT_PATH}/Goals/2026/_monthly/YYYY-MM.md`

---

## What "Done" Looks Like

Running `python summarizer.py` on a real week of notes should produce:

1. A one-sentence headline capturing the week's theme
2. Highlights grouped by category (Work, Writing, Learning, Personal, Links)
3. Goal progress assessment with evidence pulled from the notes
4. A list of saved URLs
5. Open threads -- incomplete tasks, unresolved ideas, things to follow up on

The open threads section is the most valuable output. It surfaces things that got noted but not acted on.

---

## What This Tool Is Not

- Not a journal generator. It summarizes what's already there; it does not write new content.
- Not a task manager. It surfaces open threads but does not update checkboxes.
- Not a full vault summarizer. Reads only `Timeline/YYYY-MM-DD.md` files for the target week.

---

## Series Context

| What          | Detail                                                           |
| ------------- | ---------------------------------------------------------------- |
| Tool #        | 4                                                                |
| Mode          | Single-shot                                                      |
| Trigger       | Scheduled (weekly) or Manual                                     |
| Series post   | Post 7: The Summarizer in Your Pocket                            |
| Composes with | Tool #10 (Goal Progress Tracker) consumes `goal_progress` output |
| Shares        | ModelClient with all other tools in the series                   |

---

## Build Order

1. `client.py` -- ModelClient (copy from Tool #1 if already built)
2. `schema.py` -- Pydantic models
3. `notes.py` -- vault discovery, file globbing, note parsing
4. `prompts.py` -- system prompt with extraction rules and schema spec
5. `summarizer.py` -- CLI wiring
6. `display.py` -- Rich output formatting

Test with the `examples/sample-week/` directory before pointing at the real vault.
