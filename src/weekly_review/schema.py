
from pydantic import BaseModel, Field


class WeeklyHighlight(BaseModel):
    category: str = Field(..., description="One of: Work, Learning, Writing, Personal, Links")
    summary: str | None = Field(default="", description="1-2 sentences capturing the essence")
    items: list[str] | None = Field(default_factory=list, description="Specific bullet points")

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
