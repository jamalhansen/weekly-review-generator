from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from .schema import WeekReview

def display_week_review(review: WeekReview):
    console = Console()
    
    console.print(f"\n[bold blue]Week of {review.week_of}[/bold blue]")
    console.print(Panel(review.headline or "Weekly Summary", title="[bold]Summary[/bold]", border_style="blue"))
    
    if review.highlights:
        for highlight in review.highlights:
            # Skip empty highlights if the LLM didn't follow instructions
            if not highlight.summary and not (highlight.items and len(highlight.items) > 0):
                continue
                
            console.print(f"\n[bold cyan]{highlight.category}[/bold cyan]")
            
            table = Table(box=None, show_header=False, expand=True, padding=(0, 0, 0, 2))
            if highlight.summary:
                table.add_row(f"[italic]{highlight.summary}[/italic]")
            
            if highlight.items:
                for item in highlight.items:
                    table.add_row(f"• {item}")
            
            console.print(table)

    if review.links_saved:
        console.print("\n[bold yellow]Links Saved[/bold yellow]")
        for link in review.links_saved:
            console.print(f"[underline]{link}[/underline]")

    if review.open_threads:
        console.print("\n[bold red]Open Threads[/bold red]")
        for thread in review.open_threads:
            console.print(f"  {thread}")

    console.print(f"\n[dim]Input: {review.word_count_input} words[/dim]\n")
