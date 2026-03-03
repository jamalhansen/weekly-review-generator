from schema import WeekReview

def format_as_markdown(review: WeekReview) -> str:
    """Format the week review as Obsidian-compatible Markdown."""
    lines = []
    lines.append(f"# Weekly Review: {review.week_of}")
    lines.append(f"\n> {review.headline}\n")
    
    if review.highlights:
        lines.append("## Highlights")
        for highlight in review.highlights:
            lines.append(f"### {highlight.category}")
            lines.append(f"_{highlight.summary}_")
            if highlight.items:
                for item in highlight.items:
                    lines.append(f"- {item}")
            lines.append("")

    if review.links_saved:
        lines.append("## Links Saved")
        for link in review.links_saved:
            lines.append(f"- {link}")
        lines.append("")

    if review.open_threads:
        lines.append("## Open Threads")
        for thread in review.open_threads:
            # Format as an Obsidian task
            lines.append(f"- [ ] {thread}")
        lines.append("")

    lines.append("---")
    lines.append(f"**Word Count Input:** {review.word_count_input}")
    
    return "\n".join(lines)
