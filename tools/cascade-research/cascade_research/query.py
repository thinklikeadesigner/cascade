import json
import tempfile
import webbrowser
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from .ingest import get_collection

console = Console()


def _run_query(query_text: str, top_k: int, doc_type: str = None,
               source_dir: str = None):
    """Run the query and return parsed results. Returns None if empty."""
    collection = get_collection()

    if collection.count() == 0:
        console.print("[yellow]Collection is empty. Run:[/yellow] cascade-research ingest")
        return None

    where_conditions = []
    if doc_type:
        where_conditions.append({"doc_type": doc_type})
    if source_dir:
        where_conditions.append({"source_dir": source_dir})

    where = None
    if len(where_conditions) == 1:
        where = where_conditions[0]
    elif len(where_conditions) > 1:
        where = {"$and": where_conditions}

    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"][0]:
        console.print("[yellow]No results found.[/yellow]")
        return None

    parsed = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        score = 1 - distance
        section = " > ".join(
            filter(None, [meta.get("h1", ""), meta.get("h2", ""), meta.get("h3", "")])
        )
        parsed.append({
            "text": results["documents"][0][i],
            "source": meta.get("source_file", ""),
            "doc_type": meta.get("doc_type", ""),
            "section": section,
            "score": round(score, 3),
        })
    return parsed


def _sanitize(text: str) -> str:
    """Clean text for Mermaid node labels. Strip characters that break syntax."""
    text = text.replace('"', "'").replace("\n", " ").replace("\r", " ")
    text = text.replace("<", "").replace(">", "")
    text = text.replace("(", "").replace(")", "")
    text = text.replace("[", "").replace("]", "")
    text = text.replace("{", "").replace("}", "")
    text = text.replace("#", "").replace("`", "").replace("|", "-")
    text = text.replace("&", "and")
    # Collapse whitespace
    text = " ".join(text.split())
    # Truncate long labels
    if len(text) > 60:
        text = text[:57] + "..."
    return text


def search(query_text: str, top_k: int = 5, doc_type: str = None,
           source_dir: str = None, raw: bool = False,
           mermaid: bool = False, mermaid_open: bool = False):
    """Search the collection and display results."""
    parsed = _run_query(query_text, top_k, doc_type, source_dir)
    if parsed is None:
        return

    if raw:
        output = {"query": query_text, "results": parsed}
        print(json.dumps(output, indent=2))
        return

    if mermaid_open:
        _render_mermaid_html(query_text, parsed)
        return

    if mermaid:
        _render_mermaid(query_text, parsed)
        return

    # Pretty output
    console.print(
        f"\n[bold]Found {len(parsed)} results for:[/bold] \"{query_text}\"\n"
    )

    for i, r in enumerate(parsed):
        header = f"[{i + 1}] {r['source']}"
        if r["section"]:
            header += f" > {r['section']}"
        header += f"  (score: {r['score']:.2f})"

        text = r["text"]
        if len(text) > 500:
            text = text[:500] + "..."

        border = "dim" if r["score"] < 0.3 else ("green" if r["score"] > 0.5 else "yellow")
        console.print(Panel(text, title=header, title_align="left", border_style=border))


def _render_mermaid(query_text: str, results: list[dict]):
    """Render results as raw Mermaid mindmap code."""
    src, _ = _build_mermaid_source(query_text, results)
    print(f"```mermaid\n{src}\n```")


def _build_mermaid_source(query_text: str, results: list[dict]):
    """Build raw Mermaid mindmap source (no fences).
    Returns (mermaid_source, label_to_card_map) where label_to_card_map maps
    the exact rendered node label text to result card indices."""
    by_file = {}
    # Track original index in results list
    for i, r in enumerate(results):
        source = r["source"]
        if source not in by_file:
            by_file[source] = []
        by_file[source].append((i, r))

    safe_query = _sanitize(query_text)
    lines = ["mindmap", f'  root("{safe_query}")']

    label_to_card = {}
    node_id = 0
    for source, hits in by_file.items():
        filename = source.split("/")[-1].replace(".md", "")
        safe_filename = _sanitize(filename)
        lines.append(f'    f{node_id}["{safe_filename}"]')
        node_id += 1
        for card_idx, hit in hits:
            score_pct = int(hit["score"] * 100)
            if hit["section"]:
                deepest = hit["section"].split(" > ")[-1]
                label = _sanitize(deepest)
            else:
                label = _sanitize(hit["text"][:50])
            full_label = f"{label} - {score_pct}%"
            lines.append(f'      n{node_id}["{full_label}"]')
            label_to_card[full_label] = card_idx
            node_id += 1

    return "\n".join(lines), label_to_card


def _render_mermaid_html(query_text: str, results: list[dict]):
    """Render results as a Mermaid diagram in the browser."""
    mermaid_src, node_to_card = _build_mermaid_source(query_text, results)

    # Build result cards — store raw markdown text in data attributes for JS rendering
    cards_html = ""
    for i, r in enumerate(results):
        score_pct = int(r["score"] * 100)
        # Escape for safe embedding in HTML data attribute
        raw_text = r["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        section = r["section"] if r["section"] else ""
        cards_html += f"""
        <div class="card" data-index="{i}">
          <div class="card-header">
            <span class="score">{score_pct}%</span>
            <span class="source">{r["source"]}</span>
          </div>
          {"<div class='section'>" + section + "</div>" if section else ""}
          <div class="card-text" data-markdown="{raw_text}"></div>
        </div>"""

    # Serialize node-to-card mapping for JS
    node_map_json = json.dumps(node_to_card)

    safe_query_html = query_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    result_count = len(results)

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>cascade-research: {safe_query_html}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0D0B0E; color: #F8FAFC; font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}

  /* Header */
  .header {{
    height: 52px; display: flex; align-items: center; padding: 0 1.25rem;
    background: #110E12;
    border-bottom: 1px solid #2A1F22;
    gap: 0.75rem; flex-shrink: 0;
  }}
  .logo {{ display: flex; align-items: center; gap: 0.4rem; font-weight: 700; font-size: 0.85rem; color: #EF4444; letter-spacing: -0.02em; }}
  .logo svg {{ flex-shrink: 0; }}
  .header-query {{
    font-size: 0.8rem; color: #94A3B8; flex: 1;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .header-query span {{ color: #F8FAFC; font-weight: 500; }}
  .header-badge {{
    font-size: 0.7rem; color: #94A3B8; background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.15);
    padding: 3px 8px; border-radius: 99px; font-weight: 500;
  }}
  .zoom-controls {{ display: flex; gap: 4px; }}
  .zoom-btn {{
    width: 28px; height: 28px; border-radius: 6px; border: 1px solid #2A1F22;
    background: rgba(255,255,255,0.03); color: #94A3B8; font-size: 1rem; cursor: pointer;
    display: flex; align-items: center; justify-content: center; transition: all 0.15s;
  }}
  .zoom-btn:hover {{ background: rgba(239,68,68,0.1); color: #F8FAFC; border-color: rgba(239,68,68,0.3); }}

  /* Layout */
  .container {{ display: flex; height: calc(100vh - 52px); }}

  /* Diagram */
  .diagram {{
    flex: 1; overflow: hidden; position: relative; cursor: grab;
    background:
      radial-gradient(circle at 50% 50%, rgba(239,68,68,0.04) 0%, transparent 70%),
      linear-gradient(rgba(239,68,68,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(239,68,68,0.03) 1px, transparent 1px);
    background-size: 100% 100%, 40px 40px, 40px 40px;
  }}
  .diagram.grabbing {{ cursor: grabbing; }}
  .diagram svg {{ position: absolute; transform-origin: 0 0; }}

  /* Resize handle */
  .resize-handle {{
    width: 6px; cursor: col-resize; flex-shrink: 0;
    background: #2A1F22; position: relative; z-index: 10;
    transition: background 0.15s;
  }}
  .resize-handle:hover, .resize-handle.active {{
    background: #EF4444;
  }}

  /* Sidebar */
  .sidebar {{
    width: 420px; border-left: none;
    overflow-y: auto; padding: 1rem; flex-shrink: 0;
    background: #110E12;
  }}
  .sidebar::-webkit-scrollbar {{ width: 6px; }}
  .sidebar::-webkit-scrollbar-track {{ background: transparent; }}
  .sidebar::-webkit-scrollbar-thumb {{ background: rgba(239,68,68,0.2); border-radius: 3px; }}
  .sidebar-label {{
    font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: #94A3B8; font-weight: 600; margin-bottom: 0.75rem;
  }}

  /* Cards */
  .card {{
    background: #1A1215; border: 1px solid #2A1F22;
    border-radius: 10px; padding: 0.85rem; margin-bottom: 0.6rem;
    transition: border-color 0.2s, background 0.2s;
  }}
  .card:hover {{ border-color: rgba(239,68,68,0.3); background: rgba(239,68,68,0.03); }}
  .card.active {{ border-color: #EF4444; background: rgba(239,68,68,0.08); box-shadow: 0 0 20px rgba(239,68,68,0.15); }}
  .card-header {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }}
  .score {{
    font-size: 0.65rem; font-weight: 700; padding: 2px 7px; border-radius: 5px;
    letter-spacing: 0.02em;
  }}
  .score-high {{ background: rgba(52,211,153,0.15); color: #34d399; }}
  .score-mid {{ background: rgba(251,191,36,0.15); color: #fbbf24; }}
  .score-low {{ background: rgba(255,255,255,0.06); color: #94A3B8; }}
  .source {{
    font-size: 0.75rem; color: #EF4444; font-weight: 500;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .section {{
    font-size: 0.7rem; color: #94A3B8; margin-bottom: 0.4rem;
    padding-left: 0.25rem; border-left: 2px solid rgba(239,68,68,0.3);
  }}

  /* Markdown content */
  .card-text {{ font-size: 0.78rem; color: #CBD5E1; line-height: 1.55; }}
  .card-text p {{ margin: 0.3em 0; }}
  .card-text strong {{ color: #F8FAFC; font-weight: 600; }}
  .card-text em {{ color: #F87171; font-style: italic; }}
  .card-text code {{
    background: rgba(239,68,68,0.1); padding: 1px 5px; border-radius: 4px;
    font-size: 0.85em; color: #F87171; font-family: 'SF Mono', 'Fira Code', monospace;
  }}
  .card-text pre {{
    background: #1A1215; padding: 0.6em; border-radius: 6px;
    overflow-x: auto; margin: 0.5em 0; border: 1px solid #2A1F22;
  }}
  .card-text pre code {{ padding: 0; background: none; }}
  .card-text ul, .card-text ol {{ padding-left: 1.4em; margin: 0.3em 0; }}
  .card-text li {{ margin: 0.15em 0; }}
  .card-text li::marker {{ color: #94A3B8; }}
  .card-text table {{ border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 0.9em; }}
  .card-text th, .card-text td {{
    border: 1px solid #2A1F22; padding: 5px 8px; text-align: left;
  }}
  .card-text th {{ background: #1A1215; color: #F8FAFC; font-weight: 600; font-size: 0.85em; }}
  .card-text blockquote {{
    border-left: 3px solid rgba(239,68,68,0.3); padding-left: 0.7em;
    color: #94A3B8; margin: 0.4em 0;
  }}
  .card-text h1, .card-text h2, .card-text h3, .card-text h4 {{
    color: #F8FAFC; margin: 0.5em 0 0.2em; font-weight: 600;
  }}
  .card-text h1 {{ font-size: 1.05em; }}
  .card-text h2 {{ font-size: 0.95em; }}
  .card-text h3 {{ font-size: 0.88em; }}
  .card-text hr {{ border: none; border-top: 1px solid #2A1F22; margin: 0.6em 0; }}

  /* Mermaid overrides — force Blood Moon on all elements */
  .diagram svg text, .diagram svg tspan {{
    fill: #F8FAFC !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    font-size: 14px !important;
  }}
  .diagram svg foreignObject * {{
    color: #F8FAFC !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
  }}
  .diagram svg rect, .diagram svg circle, .diagram svg polygon, .diagram svg ellipse {{
    fill: #1A0A0E !important;
    stroke: #EF4444 !important;
    stroke-width: 1.5px !important;
    filter: drop-shadow(0 3px 12px rgba(239,68,68,0.15));
  }}
  .diagram svg path {{
    stroke: #7F1D1D !important;
    stroke-width: 2px !important;
  }}
  /* Prevent Mermaid background rect from getting red */
  .diagram svg > rect {{
    fill: transparent !important;
    stroke: none !important;
    filter: none !important;
  }}
</style>
</head>
<body>
<div class="header">
  <div class="logo">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M13 5l7 7-7 7" stroke="#EF4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M4 5l7 7-7 7" stroke="#EF4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>
    </svg>
    cascade-research
  </div>
  <div class="header-query">search: <span>{safe_query_html}</span></div>
  <div class="header-badge">{result_count} results</div>
  <div class="zoom-controls">
    <button class="zoom-btn" id="zoom-out" title="Zoom out">-</button>
    <button class="zoom-btn" id="zoom-fit" title="Fit to view">o</button>
    <button class="zoom-btn" id="zoom-in" title="Zoom in">+</button>
  </div>
</div>
<div class="container">
  <div class="diagram">
    <pre class="mermaid">
{mermaid_src}
    </pre>
  </div>
  <div class="resize-handle" id="resize-handle"></div>
  <div class="sidebar">
    <div class="sidebar-label">Matching chunks</div>
    {cards_html}
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'dark',
  }});

  // Force Blood Moon palette on all Mermaid SVG elements after render
  function fixMermaidColors() {{
    const svg = document.querySelector('.diagram svg');
    if (!svg) return;

    // Make the SVG background transparent
    const bgRect = svg.querySelector(':scope > rect');
    if (bgRect) {{
      bgRect.setAttribute('fill', 'transparent');
      bgRect.removeAttribute('stroke');
      bgRect.style.filter = 'none';
    }}

    // Force all shape fills to uniform dark red
    svg.querySelectorAll('rect, circle, polygon, ellipse').forEach(el => {{
      // Skip the background rect
      if (el === bgRect) return;
      // Skip tiny decorative elements
      const w = el.getAttribute('width');
      const r = el.getAttribute('r');
      if ((w && parseFloat(w) < 5) || (r && parseFloat(r) < 3)) return;

      el.style.setProperty('fill', '#1A0A0E', 'important');
      el.style.setProperty('stroke', '#EF4444', 'important');
      el.style.setProperty('stroke-width', '1.5px', 'important');
      el.style.setProperty('filter', 'drop-shadow(0 3px 12px rgba(239,68,68,0.15))', 'important');
    }});

    // Force all text to white — covers SVG text AND foreignObject HTML
    svg.querySelectorAll('text, tspan').forEach(el => {{
      el.style.setProperty('fill', '#F8FAFC', 'important');
      el.style.setProperty('font-family', 'Inter, -apple-system, sans-serif', 'important');
    }});
    svg.querySelectorAll('foreignObject, foreignObject *').forEach(el => {{
      el.style.setProperty('color', '#F8FAFC', 'important');
      el.style.setProperty('font-family', 'Inter, -apple-system, sans-serif', 'important');
    }});

    // Force connector lines to dark red
    svg.querySelectorAll('path, line').forEach(el => {{
      const fill = el.getAttribute('fill');
      if (!fill || fill === 'none' || fill === 'transparent') {{
        el.style.setProperty('stroke', '#7F1D1D', 'important');
        el.style.setProperty('stroke-width', '2px', 'important');
      }} else {{
        // Filled paths (like arrowheads) get the same treatment as shapes
        el.style.setProperty('fill', '#1A0A0E', 'important');
        el.style.setProperty('stroke', '#EF4444', 'important');
      }}
    }});
  }}

  // Run multiple times to catch async Mermaid rendering
  setTimeout(fixMermaidColors, 300);
  setTimeout(fixMermaidColors, 600);
  setTimeout(fixMermaidColors, 1200);

  // Label text → card index mapping from Python
  const labelToCard = {node_map_json};

  // Click-to-scroll: click a diagram node, highlight + scroll the matching card
  function setupNodeClicks() {{
    const svg = document.querySelector('.diagram svg');
    if (!svg) return;

    // Walk every element that could be a clickable node
    svg.querySelectorAll('g').forEach(group => {{
      // Get the text content from foreignObject or text elements
      const textEl = group.querySelector('foreignObject, text');
      if (!textEl) return;
      const nodeText = textEl.textContent.trim();

      // Check if this node's text matches a known label
      if (!(nodeText in labelToCard)) return;

      group.style.cursor = 'pointer';
      group.addEventListener('click', (e) => {{
        e.stopPropagation();
        const cardIdx = labelToCard[nodeText];
        const card = document.querySelector(`.card[data-index="${{cardIdx}}"]`);
        if (!card) return;

        // Clear previous active
        document.querySelectorAll('.card.active').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        // Auto-clear after 3s
        setTimeout(() => card.classList.remove('active'), 3000);
      }});
    }});
  }}

  setTimeout(setupNodeClicks, 700);
  setTimeout(setupNodeClicks, 1300);

  // Render markdown in cards
  document.querySelectorAll('.card-text[data-markdown]').forEach(el => {{
    const md = el.getAttribute('data-markdown');
    el.innerHTML = marked.parse(md);
  }});

  // Score colors
  document.querySelectorAll('.score').forEach(el => {{
    const pct = parseInt(el.textContent);
    if (pct >= 50) el.classList.add('score-high');
    else if (pct >= 30) el.classList.add('score-mid');
    else el.classList.add('score-low');
  }});

  // Pan & zoom
  const container = document.querySelector('.diagram');
  let scale = 1, panX = 0, panY = 0, dragging = false, resizing = false, startX, startY;

  function centerDiagram() {{
    const svg = container.querySelector('svg');
    if (!svg) return;
    const cr = container.getBoundingClientRect();
    const fitScale = Math.min(
      cr.width / svg.viewBox.baseVal.width,
      cr.height / svg.viewBox.baseVal.height,
      1.5
    ) * 0.85;
    scale = fitScale;
    panX = (cr.width - svg.viewBox.baseVal.width * scale) / 2;
    panY = (cr.height - svg.viewBox.baseVal.height * scale) / 2;
    applyTransform(svg);
  }}

  function applyTransform(svg) {{
    svg.style.transform = `translate(${{panX}}px, ${{panY}}px) scale(${{scale}})`;
    svg.style.transition = dragging ? 'none' : 'transform 0.15s ease-out';
  }}

  function zoom(delta, cx, cy) {{
    const svg = container.querySelector('svg');
    if (!svg) return;
    const rect = container.getBoundingClientRect();
    const mouseX = cx !== undefined ? cx - rect.left : rect.width / 2;
    const mouseY = cy !== undefined ? cy - rect.top : rect.height / 2;
    const newScale = Math.min(Math.max(scale * delta, 0.15), 6);
    panX = mouseX - (mouseX - panX) * (newScale / scale);
    panY = mouseY - (mouseY - panY) * (newScale / scale);
    scale = newScale;
    applyTransform(svg);
  }}

  container.addEventListener('wheel', (e) => {{
    e.preventDefault();
    zoom(e.deltaY > 0 ? 0.92 : 1.08, e.clientX, e.clientY);
  }}, {{ passive: false }});

  container.addEventListener('mousedown', (e) => {{
    if (resizing) return;
    dragging = true;
    startX = e.clientX - panX;
    startY = e.clientY - panY;
    container.classList.add('grabbing');
  }});
  window.addEventListener('mousemove', (e) => {{
    if (!dragging || resizing) return;
    panX = e.clientX - startX;
    panY = e.clientY - startY;
    const svg = container.querySelector('svg');
    if (svg) applyTransform(svg);
  }});
  window.addEventListener('mouseup', () => {{
    dragging = false;
    container.classList.remove('grabbing');
  }});

  document.getElementById('zoom-in').addEventListener('click', () => zoom(1.25));
  document.getElementById('zoom-out').addEventListener('click', () => zoom(0.75));
  document.getElementById('zoom-fit').addEventListener('click', centerDiagram);

  setTimeout(centerDiagram, 600);

  // Resizable panels
  const handle = document.getElementById('resize-handle');
  const sidebar = document.querySelector('.sidebar');

  handle.addEventListener('mousedown', (e) => {{
    e.preventDefault();
    resizing = true;
    handle.classList.add('active');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }});

  window.addEventListener('mousemove', (e) => {{
    if (!resizing) return;
    const containerRect = document.querySelector('.container').getBoundingClientRect();
    const newWidth = containerRect.right - e.clientX;
    const clamped = Math.min(Math.max(newWidth, 200), containerRect.width - 200);
    sidebar.style.width = clamped + 'px';
  }});

  window.addEventListener('mouseup', () => {{
    if (resizing) {{
      resizing = false;
      handle.classList.remove('active');
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }}
  }});
</script>
</body>
</html>"""

    tmp = tempfile.NamedTemporaryFile(suffix=".html", prefix="cascade-research-", delete=False)
    tmp.write(html.encode("utf-8"))
    tmp.close()

    console.print(f"[dim]Opened:[/dim] {tmp.name}")
    webbrowser.open(f"file://{tmp.name}")


def list_indexed():
    """List all indexed files and their chunk counts."""
    collection = get_collection()
    all_data = collection.get(include=["metadatas"])

    if not all_data["ids"]:
        console.print("[yellow]Collection is empty. Run:[/yellow] cascade-research ingest")
        return

    file_counts = {}
    for meta in all_data["metadatas"]:
        source = meta.get("source_file", "unknown")
        doc_type = meta.get("doc_type", "unknown")
        if source not in file_counts:
            file_counts[source] = {"count": 0, "doc_type": doc_type}
        file_counts[source]["count"] += 1

    from rich.table import Table
    table = Table(title="Indexed Files")
    table.add_column("File", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Chunks", justify="right", style="green")

    for source in sorted(file_counts.keys()):
        info = file_counts[source]
        table.add_row(source, info["doc_type"], str(info["count"]))

    console.print(table)
    console.print(
        f"\n[bold]Total:[/bold] {len(file_counts)} files, {len(all_data['ids'])} chunks"
    )


def show_stats():
    """Show collection statistics."""
    collection = get_collection()
    count = collection.count()

    if count == 0:
        console.print("[yellow]Collection is empty. Run:[/yellow] cascade-research ingest")
        return

    all_data = collection.get(include=["metadatas"])

    doc_types = {}
    source_dirs = {}
    for meta in all_data["metadatas"]:
        dt = meta.get("doc_type", "unknown")
        sd = meta.get("source_dir", "unknown")
        doc_types[dt] = doc_types.get(dt, 0) + 1
        source_dirs[sd] = source_dirs.get(sd, 0) + 1

    console.print(f"\n[bold]Collection:[/bold] {collection.name}")
    console.print(f"[bold]Total chunks:[/bold] {count}")

    from rich.table import Table

    table = Table(title="By Document Type")
    table.add_column("Type", style="magenta")
    table.add_column("Chunks", justify="right", style="green")
    for dt, c in sorted(doc_types.items()):
        table.add_row(dt, str(c))
    console.print(table)

    table2 = Table(title="By Directory")
    table2.add_column("Directory", style="cyan")
    table2.add_column("Chunks", justify="right", style="green")
    for sd, c in sorted(source_dirs.items()):
        table2.add_row(sd, str(c))
    console.print(table2)
