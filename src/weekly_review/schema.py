
from pydantic import BaseModel, Field, field_validator


def _coerce_str_to_list(v):
    """A small local model sometimes returns a bare string instead of a
    list for a list[str] field -- confirmed live 2026-09-20: phi4-mini
    returned a plain string for links_saved and suggested_intentions,
    which pydantic rejected outright, silently dropping that week's
    review. A single string is what the model meant as a one-item list,
    not a reason to reject the whole response."""
    if isinstance(v, str):
        return [v]
    return v


class WeeklyHighlight(BaseModel):
    category: str = Field(..., description="One of: Work, Learning, Writing, Personal, Links")
    summary: str | None = Field(default="", description="1-2 sentences capturing the essence")
    items: list[str] | None = Field(default_factory=list, description="Specific bullet points")

    @field_validator("items", mode="before")
    @classmethod
    def _coerce_items(cls, v):
        return _coerce_str_to_list(v)

class WeekReview(BaseModel):
    week_of: str = Field(..., description="ISO date of the Monday of the week (YYYY-MM-DD)")
    headline: str | None = Field(default="Weekly Summary", description="One sentence capturing the theme of the week")
    key_insight: str | None = Field(
        default=None,
        description=(
            "2-3 sentences naming the single most generative moment or session of the week — "
            "the entry that produced the most intellectual or creative output. Include the date."
        ),
    )
    highlights: list[WeeklyHighlight] | None = Field(default_factory=list)
    links_saved: list[str] | None = Field(default_factory=list, description="URLs found in the notes")
    suggested_intentions: list[str] | None = Field(default_factory=list, description="3 suggested intentions for the coming week")
    word_count_input: int = Field(..., description="Total words fed to the model")

    @field_validator("links_saved", "suggested_intentions", mode="before")
    @classmethod
    def _coerce_lists(cls, v):
        return _coerce_str_to_list(v)
