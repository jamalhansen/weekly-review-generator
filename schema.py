from typing import List, Optional, Union
from pydantic import BaseModel, Field

class WeeklyHighlight(BaseModel):
    category: str = Field(..., description="e.g., Work, Learning, Writing, Personal, Links")
    summary: Optional[str] = Field(default="", description="1-2 sentences capturing the essence")
    items: Optional[List[str]] = Field(default_factory=list, description="Specific bullet points")

class WeekReview(BaseModel):
    week_of: str = Field(..., description="ISO date of the Monday of the week (YYYY-MM-DD)")
    headline: Optional[str] = Field(default="Weekly Summary", description="One sentence capturing the theme of the week")
    highlights: Optional[List[WeeklyHighlight]] = Field(default_factory=list)
    links_saved: Optional[List[str]] = Field(default_factory=list, description="URLs found in the notes")
    open_threads: Optional[List[str]] = Field(default_factory=list, description="Unresolved items, incomplete tasks, or loose thoughts")
    word_count_input: int = Field(..., description="Total words fed to the model")
