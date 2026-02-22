import click

from .config import get_query_defaults


@click.group()
def main():
    """Cascade Research -- semantic search over your research files."""
    pass


@main.command()
@click.argument("file", required=False)
def ingest(file):
    """Ingest markdown files into the vector database.

    Without arguments: scan all configured directories, index new/changed files.
    With FILE: index a single file.
    """
    from .ingest import ingest_all, ingest_single

    if file:
        ingest_single(file)
    else:
        ingest_all(force=False)


@main.command()
@click.argument("query_text")
@click.option("--top-k", "-k", default=None, type=int, help="Number of results to return")
@click.option("--type", "doc_type", default=None, help="Filter: research, synthesis, planning")
@click.option("--dir", "source_dir", default=None, help="Filter by source directory")
@click.option("--raw", is_flag=True, help="Output JSON for agent consumption")
@click.option("--mermaid", is_flag=True, help="Output as Mermaid mindmap code")
@click.option("--mermaid-open", is_flag=True, help="Render Mermaid diagram in browser")
def query(query_text, top_k, doc_type, source_dir, raw, mermaid, mermaid_open):
    """Search your research files semantically."""
    from .query import search

    defaults = get_query_defaults()
    if top_k is None:
        top_k = defaults["top_k"]

    search(query_text, top_k=top_k, doc_type=doc_type, source_dir=source_dir,
           raw=raw, mermaid=mermaid, mermaid_open=mermaid_open)


@main.command(name="list")
def list_cmd():
    """List all indexed files and chunk counts."""
    from .query import list_indexed
    list_indexed()


@main.command()
def stats():
    """Show collection statistics."""
    from .query import show_stats
    show_stats()


@main.command()
def rules():
    """Print content rules for research generation."""
    from .config import load_config
    from rich.console import Console
    console = Console()

    config = load_config()
    rule_list = config.get("rules", [])
    if not rule_list:
        console.print("[yellow]No rules configured.[/yellow]")
        return

    console.print("\n[bold]Research Content Rules[/bold]\n")
    for i, rule in enumerate(rule_list, 1):
        console.print(f"  {i}. {rule}")
    console.print()


@main.command()
def rebuild():
    """Delete and rebuild the entire index from scratch."""
    from .ingest import ingest_all
    click.confirm("This will delete and rebuild the entire index. Continue?", abort=True)
    ingest_all(force=True)


if __name__ == "__main__":
    main()
