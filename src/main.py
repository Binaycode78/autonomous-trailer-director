"""
Autonomous Trailer Director — CLI Entry Point
=============================================

Usage:
    python -m src.main --episode data/ --mode mock --output sample_run/
    python -m src.main --episode data/ --mode real --output out/ --event music_rights_expired
    python -m src.main --episode data/ --mode replay --replay-dir recordings/ --output out/
    python -m src.main --episode data/ --mode mock --output out/ --event spoiler_reclassified
"""

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

# Configure rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

console = Console()

VALID_EVENTS = [
    "music_rights_expired",
    "spoiler_reclassified",
    "clickbait_requested",
    "model_unavailable",
    "scene_hallucination",
    "bias_detected",
    "dialect_subtitle_changed",
    "none",
]

VALID_MODES = ["mock", "real", "replay"]


@click.command()
@click.option(
    "--episode",
    "-e",
    default="data/",
    show_default=True,
    help="Path to the episode package directory.",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--output",
    "-o",
    default="sample_run/",
    show_default=True,
    help="Output directory for trailer EDLs and reports.",
)
@click.option(
    "--mode",
    "-m",
    default="mock",
    show_default=True,
    type=click.Choice(VALID_MODES, case_sensitive=False),
    help="LLM mode: 'mock' (no API key needed), 'real' (Groq API), 'replay' (recorded responses).",
)
@click.option(
    "--model",
    default="llama-3.3-70b-versatile",
    show_default=True,
    help="Groq model name (only used in 'real' mode).",
)
@click.option(
    "--event",
    default=None,
    type=click.Choice(VALID_EVENTS, case_sensitive=False),
    help="Surprise event to inject during the run.",
)
@click.option(
    "--replay-dir",
    default=None,
    help="Directory of recorded LLM responses (only used in 'replay' mode).",
    type=click.Path(file_okay=False, dir_okay=True),
)
@click.option(
    "--budget",
    default=2.0,
    show_default=True,
    help="Maximum total cost in USD for LLM calls.",
    type=float,
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output.",
)
def main(episode, output, mode, model, event, replay_dir, budget, verbose):
    """
    🎬 Autonomous Trailer Director

    Creates three audience-specific trailer Edit Decision Lists (EDLs)
    from a single episode, enforcing spoiler protection, rights compliance,
    rating policies, and cultural respect.

    Audiences: Family | Young Adult | Dialect-Region
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate mode-specific requirements
    if mode == "real":
        import os
        if not os.environ.get("GROQ_API_KEY"):
            console.print(
                "[bold red]Error:[/bold red] GROQ_API_KEY environment variable not set. "
                "Use --mode mock for zero-API-key evaluation.",
                style="red",
            )
            sys.exit(1)

    if mode == "replay" and not replay_dir:
        console.print(
            "[bold red]Error:[/bold red] --replay-dir is required when --mode replay.",
            style="red",
        )
        sys.exit(1)

    # Print header
    console.print(
        Panel.fit(
            "[bold cyan]🎬 Autonomous Trailer Director[/bold cyan]\n"
            f"[dim]Episode: {episode} | Mode: {mode} | Event: {event or 'none'}[/dim]",
            border_style="cyan",
        )
    )

    # Import here to avoid circular imports at module level
    from src.orchestrator import TrailerDirectorOrchestrator

    orchestrator = TrailerDirectorOrchestrator(
        data_dir=episode,
        output_dir=output,
        mode=mode,
        model=model,
        event=event,
        replay_dir=replay_dir,
        budget_limit=budget,
    )

    try:
        summary = orchestrator.run()
        _print_summary(summary, output)
    except KeyboardInterrupt:
        console.print("\n[yellow]Run cancelled by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)


def _print_summary(summary: dict, output_dir: str):
    """Print a rich summary table to the console."""
    console.print()

    # Status table
    table = Table(title="Trailer Generation Summary", show_header=True, header_style="bold cyan")
    table.add_column("Trailer", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("File")

    status_styles = {
        "PASS": "[bold green]✅ PASS[/bold green]",
        "PASS_WITH_WARNINGS": "[bold yellow]⚠️ PASS+WARN[/bold yellow]",
        "FAIL": "[bold red]❌ FAIL[/bold red]",
        "FAIL_UNRESOLVED": "[bold red]🚫 UNRESOLVED[/bold red]",
        "HUMAN_APPROVAL_REQUIRED": "[bold magenta]👤 NEEDS APPROVAL[/bold magenta]",
    }

    file_map = {
        "family_v1": "family_trailer.json",
        "young_adult_v1": "young_adult_trailer.json",
        "dialect_region_v1": "dialect_region_trailer.json",
    }

    for trailer_id, status in summary["trailer_statuses"].items():
        table.add_row(
            trailer_id,
            status_styles.get(status, status),
            file_map.get(trailer_id, f"{trailer_id}.json"),
        )

    console.print(table)

    # Cost summary
    console.print(
        f"\n[dim]💰 Cost: [bold]${summary['total_cost_usd']:.4f}[/bold] | "
        f"LLM Calls: {summary['total_llm_calls']} | "
        f"Output: [cyan]{output_dir}[/cyan][/dim]"
    )

    if summary.get("event_injected"):
        console.print(
            f"[yellow]⚡ Surprise event injected: [bold]{summary['event_injected']}[/bold][/yellow]"
        )

    console.print(
        f"\n[green]✓ Outputs saved to:[/green] [cyan]{output_dir}[/cyan]\n"
        f"  • story_map.json\n"
        f"  • constraint_map.json\n"
        f"  • family_trailer.json\n"
        f"  • young_adult_trailer.json\n"
        f"  • dialect_region_trailer.json\n"
        f"  • validation_report.md\n"
        f"  • decision_log.jsonl"
    )


if __name__ == "__main__":
    main()
