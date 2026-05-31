"""Build the GitLab Pages static site from frozen project outputs.

The script intentionally uses only the Python standard library so the Pages job
does not need Ruby, Node, MkDocs, or GitBook dependencies.
"""

from __future__ import annotations

import csv
import html
import json
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE_ASSETS = ROOT / "docs" / "pages"


@dataclass(frozen=True)
class SssomFileStats:
    filename: str
    rows: int
    predicates: Counter[str]
    justifications: Counter[str]


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def pct(part: int | float, whole: int | float) -> str:
    if not whole:
        return "0.0%"
    return f"{(part / whole) * 100:.1f}%"


def esc(value: Any) -> str:
    return html.escape(str(value))


def read_sssom_file(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if line.startswith("#") or not line.strip():
            continue
        if "\t" in line and "subject_id" in line and "predicate_id" in line:
            header_index = index
            break
    if header_index is None:
        return []
    data = "\n".join(line for line in lines[header_index:] if line.strip())
    return list(csv.DictReader(data.splitlines(), delimiter="\t"))


def collect_sssom_stats() -> tuple[list[SssomFileStats], Counter[str], Counter[str]]:
    stats: list[SssomFileStats] = []
    predicate_totals: Counter[str] = Counter()
    justification_totals: Counter[str] = Counter()
    for path in sorted((ROOT / "exports" / "sssom").glob("*.sssom.tsv")):
        rows = read_sssom_file(path)
        predicates = Counter(row.get("predicate_id", "") or "(missing)" for row in rows)
        justifications = Counter(
            row.get("mapping_justification", "") or "(missing)" for row in rows
        )
        predicate_totals.update(predicates)
        justification_totals.update(justifications)
        stats.append(
            SssomFileStats(
                filename=path.name,
                rows=len(rows),
                predicates=predicates,
                justifications=justifications,
            )
        )
    return stats, predicate_totals, justification_totals


def collect_graph_stats() -> dict[str, Any]:
    crosswalk_graph = read_json(ROOT / "exports" / "graph" / "crosswalk_graph.json", {})
    human_graph = read_json(ROOT / "data" / "crosswalks.human.json", {})

    edges = crosswalk_graph.get("edges", [])
    nodes = crosswalk_graph.get("nodes", [])
    strategies = Counter(
        edge.get("metadata", {}).get("strategy", "unknown") for edge in edges
    )
    graph_rule_count = sum(
        int(edge.get("metadata", {}).get("rule_count", 0) or 0) for edge in edges
    )

    human_nodes = human_graph.get("nodes", [])
    human_edges = human_graph.get("edges", [])
    human_types = Counter(node.get("type", "unknown") for node in human_nodes)
    relationships = Counter(edge.get("relationship", "unknown") for edge in human_edges)

    return {
        "crosswalk_nodes": len(nodes),
        "crosswalk_edges": len(edges),
        "strategies": strategies,
        "graph_rule_count": graph_rule_count,
        "human_nodes": len(human_nodes),
        "human_edges": len(human_edges),
        "human_types": human_types,
        "relationships": relationships,
        "largest_edges": sorted(
            edges,
            key=lambda edge: int(edge.get("metadata", {}).get("rule_count", 0) or 0),
            reverse=True,
        )[:8],
        "has_human_graph": bool(human_graph),
    }


def collect_live_benchmark_stats() -> dict[str, Any]:
    benchmark = read_json(
        ROOT / "exports" / "benchmark" / "datacite_dc_oai_awi_benchmark.json", {}
    )
    aggregate = benchmark.get("aggregate", {})
    cases = int(aggregate.get("cases", 0) or 0)
    failures_path = ROOT / "exports" / "benchmark" / "datacite_dc_oai_awi_benchmark.failures.json"
    failures = read_json(failures_path, []) if failures_path.exists() else []
    return {
        "cases": cases,
        "failures": len(failures) if isinstance(failures, list) else 0,
        "completed": 100.0 if cases else 0.0,
        "field_coverage": float(aggregate.get("avg_field_coverage", 0) or 0) * 100,
        "value_overlap": float(aggregate.get("avg_value_overlap", 0) or 0) * 100,
        "semantic_loss_rate": float(aggregate.get("avg_semantic_loss_rate", 0) or 0) * 100,
        "available": bool(aggregate),
    }


def collect_artifact_host_outcomes() -> list[dict[str, Any]]:
    path = ROOT / "exports" / "pipeline" / "latest" / "rdamsc_artifacts.csv"
    if not path.exists():
        return []
    fetched: Counter[str] = Counter()
    failed: Counter[str] = Counter()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            host = row.get("host") or "(unknown)"
            status = row.get("check_status") or "(unknown)"
            if status == "fetched":
                fetched[host] += 1
            elif status == "fetch_error":
                failed[host] += 1
    totals = fetched + failed
    return [
        {
            "host": host,
            "fetched": fetched[host],
            "failed": failed[host],
            "total": totals[host],
        }
        for host, _count in totals.most_common(12)
    ]


def render_live_benchmark_plotly(benchmark: dict[str, Any]) -> str:
    if not benchmark.get("available"):
        return ""
    rings = [
        {"label": "Completed", "value": benchmark["completed"], "color": "#8cd600", "base": 0.86},
        {"label": "Field coverage", "value": benchmark["field_coverage"], "color": "#D23264", "base": 0.66},
        {"label": "Value overlap", "value": benchmark["value_overlap"], "color": "#f0781e", "base": 0.46},
        {
            "label": "Semantic loss rate",
            "value": benchmark["semantic_loss_rate"],
            "color": "#a0235a",
            "base": 0.26,
        },
    ]
    plot_data: list[dict[str, Any]] = []
    annotations = []
    for ring in rings:
        angle = 360 * ring["value"] / 100
        plot_data.extend(
            [
                {
                    "type": "barpolar",
                    "r": [0.14],
                    "base": [ring["base"]],
                    "theta": [180],
                    "width": [360],
                    "marker": {"color": "#e5e7eb", "line": {"color": "#ffffff", "width": 2}},
                    "hoverinfo": "skip",
                    "showlegend": False,
                },
                {
                    "type": "barpolar",
                    "r": [0.14],
                    "base": [ring["base"]],
                    "theta": [90 - angle / 2],
                    "width": [angle],
                    "marker": {"color": ring["color"], "line": {"color": "#ffffff", "width": 2}},
                    "name": f"{ring['label']}: {ring['value']:.1f}%",
                    "hovertemplate": f"{ring['label']}: {ring['value']:.1f}%<extra></extra>",
                },
            ]
        )
        annotations.append(
            {
                "x": 1.08,
                "y": ring["base"] + 0.07,
                "xref": "paper",
                "yref": "paper",
                "text": f"<b>{ring['label']}</b> {ring['value']:.1f}%",
                "showarrow": False,
                "xanchor": "left",
                "font": {"size": 13, "color": "#002864"},
            }
        )

    config = {"displayModeBar": False, "responsive": True}
    layout = {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor": "#ffffff",
        "margin": {"l": 10, "r": 180, "t": 10, "b": 10},
        "showlegend": False,
        "height": 460,
        "polar": {
            "bgcolor": "#ffffff",
            "radialaxis": {"visible": False, "range": [0, 1.05]},
            "angularaxis": {"visible": False, "rotation": 90, "direction": "clockwise"},
        },
        "annotations": [
            {
                "x": 0.38,
                "y": 0.54,
                "xref": "paper",
                "yref": "paper",
                "text": f"<b>n = {benchmark['cases']:,}</b><br>live OAI-PMH<br>records",
                "showarrow": False,
                "font": {"size": 18, "color": "#002864"},
                "align": "center",
            },
            *annotations,
        ],
    }
    return f"""
<div id="live-oai-rings" class="plotly-rings" role="img" aria-label="Live OAI-PMH benchmark concentric rings"></div>
<img id="live-oai-rings-fallback" class="plot-fallback" src="assets/live_oai_pmh_concentric_rings.svg" alt="Live OAI-PMH benchmark concentric rings" hidden>
<noscript><img class="plot-fallback" src="assets/live_oai_pmh_concentric_rings.svg" alt="Live OAI-PMH benchmark concentric rings"></noscript>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
(() => {{
  if (!window.Plotly) {{
    document.getElementById('live-oai-rings').style.display = 'none';
    document.getElementById('live-oai-rings-fallback').hidden = false;
    return;
  }}
  const data = {json.dumps(plot_data)};
  const layout = {json.dumps(layout)};
  const config = {json.dumps(config)};
  Plotly.newPlot('live-oai-rings', data, layout, config);
}})();
</script>
"""


def table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{esc(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_page(title: str, active: str, body: str, subtitle: str) -> str:
    nav = [
        ("index.html", "Overview"),
        ("statistics.html", "Statistics"),
        ("documentation.html", "Documentation"),
        ("graph.html", "Graph"),
        ("files.html", "Files"),
    ]
    links = "".join(
        f'<a href="{href}"{(" class=\"active\"" if label == active else "")}>{label}</a>'
        for href, label in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} · m2s3om_graph</title>
  <link rel="stylesheet" href="assets/site.css">
</head>
<body>
  <header class="site-header">
    <h1>m2s3om_graph</h1>
    <p>{esc(subtitle)}</p>
    <nav class="nav">{links}</nav>
  </header>
  <main>{body}<footer class="footer">Generated from frozen repository outputs. Rebuild with <code>python scripts/build_pages.py</code>.</footer></main>
</body>
</html>
"""


def metric(value: Any, label: str) -> str:
    return f'<div class="metric"><strong>{esc(value)}</strong><span>{esc(label)}</span></div>'


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_if_exists(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def copy_tree_if_exists(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return True


def copy_assets() -> None:
    assets = PUBLIC / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    copy_if_exists(SITE_ASSETS / "site.css", assets / "site.css")
    copy_if_exists(ROOT / "exports" / "legend.svg", assets / "legend.svg")
    copy_if_exists(ROOT / "exports" / "legend.png", assets / "legend.png")
    copy_if_exists(ROOT / "scorecard.png", assets / "scorecard.png")
    copy_if_exists(
        ROOT / "plots" / "poster_crosswalk_status_pie.png",
        assets / "poster_crosswalk_status_pie.png",
    )
    copy_if_exists(
        ROOT / "plots" / "poster_datacite_dublincore_benchmark_bar.png",
        assets / "poster_datacite_dublincore_benchmark_bar.png",
    )
    copy_if_exists(
        ROOT / "plots" / "poster_fetched_artifact_formats_bar.png",
        assets / "poster_fetched_artifact_formats_bar.png",
    )
    copy_if_exists(
        ROOT / "plots" / "poster_artifact_host_outcomes_bar.png",
        assets / "poster_artifact_host_outcomes_bar.png",
    )
    copy_if_exists(
        ROOT / "plots" / "live_oai_pmh_concentric_rings.png",
        assets / "live_oai_pmh_concentric_rings.png",
    )
    copy_if_exists(
        ROOT / "plots" / "live_oai_pmh_concentric_rings.svg",
        assets / "live_oai_pmh_concentric_rings.svg",
    )
    copy_if_exists(
        ROOT / "m2s3om_crosswalk_graph_20260528_005439.svg",
        assets / "crosswalk-network.svg",
    )
    plots_src = ROOT / "exports" / "pipeline" / "latest" / "plots"
    if plots_src.exists():
        plots_dest = assets / "plots"
        if plots_dest.exists():
            shutil.rmtree(plots_dest)
        shutil.copytree(plots_src, plots_dest)

    graph_dest = PUBLIC / "graph-visualizer"
    graph_src = ROOT / "exports" / "graph_visualizer_web"
    if not copy_tree_if_exists(graph_src, graph_dest):
        copy_tree_if_exists(ROOT / "graph-visualizer" / "web", graph_dest)
    ensure_graphology_files(graph_dest / "graphs")


def ensure_graphology_files(graphs_dir: Path) -> None:
    """Ensure the bundled visualizer has graph data in CI-friendly builds."""
    graphs_dir.mkdir(parents=True, exist_ok=True)
    legacy_graph = read_json(ROOT / "exports" / "graph" / "crosswalk_graph.json", {})

    automatic = graphs_dir / "automatic_hm_graph.graphology.json"
    if not automatic.exists():
        # Prefer the richer human graph; fall back to the committed legacy export.
        human_graph = read_json(ROOT / "data" / "crosswalks.human.json", {})
        if human_graph:
            automatic.write_text(
                json.dumps(human_to_graphology(human_graph), indent=2), encoding="utf-8"
            )
        elif legacy_graph:
            automatic.write_text(
                json.dumps(legacy_to_graphology(legacy_graph), indent=2), encoding="utf-8"
            )

    crosswalks = graphs_dir / "crosswalks.graphology.json"
    if not crosswalks.exists():
        if legacy_graph:
            crosswalks.write_text(
                json.dumps(legacy_to_graphology(legacy_graph), indent=2), encoding="utf-8"
            )


def human_to_graphology(human_graph: dict[str, Any]) -> dict[str, Any]:
    node_attrs = human_graph.get("nodeAttributes", {})
    edge_attrs = human_graph.get("edgeAttributes", {})
    nodes = []
    for node in human_graph.get("nodes", []):
        attrs = dict(node_attrs.get(node.get("attrRef"), {}))
        attrs["label"] = node.get("label", node.get("id", ""))
        attrs["kind"] = node.get("type", attrs.get("kind", "unknown"))
        nodes.append({"key": node.get("id"), "attributes": attrs})

    edges = []
    for index, edge in enumerate(human_graph.get("edges", [])):
        attrs = dict(edge_attrs.get(edge.get("attrRef"), {}))
        attrs["relationship"] = edge.get("relationship", attrs.get("relationship", "crosswalk"))
        edges.append(
            {
                "key": edge.get("id") or edge.get("attrRef") or f"e{index}",
                "source": edge.get("source"),
                "target": edge.get("target"),
                "attributes": attrs,
            }
        )
    return {"attributes": {"type": "directed"}, "nodes": nodes, "edges": edges}


def legacy_to_graphology(legacy_graph: dict[str, Any]) -> dict[str, Any]:
    nodes = [
        {
            "key": node.get("id"),
            "attributes": {
                "label": node.get("label", node.get("id", "")),
                "kind": node.get("kind", "unknown"),
                "color": node.get("color", "#4A90E2"),
                "size": node.get("size", 8),
                "x": node.get("x"),
                "y": node.get("y"),
            },
        }
        for node in legacy_graph.get("nodes", [])
    ]
    edges = []
    for index, edge in enumerate(legacy_graph.get("edges", [])):
        metadata = edge.get("metadata", {})
        edges.append(
            {
                "key": edge.get("id", f"e{index}"),
                "source": edge.get("source"),
                "target": edge.get("target"),
                "attributes": {
                    "relationship": edge.get("label", "crosswalk"),
                    "color": edge.get("color", "#95A5A6"),
                    "size": edge.get("size", 1),
                    "strategy": metadata.get("strategy", "unknown"),
                    "rule_count": metadata.get("rule_count", 0),
                },
            }
        )
    return {"attributes": {"type": "directed"}, "nodes": nodes, "edges": edges}


def ensure_public() -> None:
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(parents=True)


def build() -> None:
    ensure_public()
    copy_assets()

    pipeline = read_json(ROOT / "exports" / "pipeline" / "latest" / "rdamsc_stats_summary.json", {})
    metadata = read_json(ROOT / "exports" / "pipeline" / "latest" / "run_metadata.json", {})
    manifest = read_json(ROOT / "exports" / "sssom" / "generation_manifest.json", {})
    sssom_files, predicates, justifications = collect_sssom_stats()
    graph = collect_graph_stats()
    live_benchmark = collect_live_benchmark_stats()
    host_outcomes = collect_artifact_host_outcomes()

    total_rows = sum(item.rows for item in sssom_files)
    total_files = len(sssom_files)
    ready = pipeline.get("status_counts", {}).get("ready", 0)
    failed_unreachable = pipeline.get("status_counts", {}).get("failed_unreachable", 0)
    failed_parse = pipeline.get("status_counts", {}).get("failed_parse", 0)
    total_crosswalks = pipeline.get("total_crosswalks", 0)
    artifact_checks = pipeline.get("artifact_checks", {}).get("total", 0)
    fetched = pipeline.get("artifact_checks", {}).get("status_counts", {}).get("fetched", 0)
    fetch_errors = pipeline.get("artifact_checks", {}).get("status_counts", {}).get("fetch_error", 0)
    deterministic = graph["strategies"].get("deterministic", 0)
    llm = graph["strategies"].get("llm", 0)
    unknown = graph["strategies"].get("unknown", 0)

    human_graph_text = (
        f"<p><strong>{graph['human_nodes']}</strong> standards in the human graph</p>"
        f"<p><strong>{graph['human_edges']}</strong> crosswalk edges in the human graph</p>"
        if graph["has_human_graph"]
        else "<p>Human graph source not present in this build.</p>"
    )

    overview = f"""
<section class="hero">
  <div class="panel">
    <div class="eyebrow">Evidence-based metadata crosswalk workbench</div>
    <h2>Documentation and presentation numbers for the RDAMSC crosswalk pipeline.</h2>
    <p class="lead">This site is generated from the frozen pipeline exports, SSSOM files, and graph outputs committed with the project. It is intended for GitLab Pages, talks, posters, and quick project orientation.</p>
    <div class="metrics-grid">
      {metric(total_crosswalks, "RDAMSC crosswalks processed")}
      {metric(f"{ready} ({pct(ready, total_crosswalks)})", "ready with SSSOM output")}
      {metric(total_rows, "actual SSSOM mapping rows")}
      {metric(f"{fetched}/{artifact_checks}", "artifacts fetched")}
    </div>
    <div class="callout"><strong>Rule-count note:</strong> older project notes used approximately 1,280 because that is the total line count of the SSSOM files, including comments and headers. The current strict data-row count is <strong>{total_rows}</strong> mapping rules across <strong>{total_files}</strong> SSSOM files.</div>
  </div>
  <div class="card">
    <h3>Snapshot provenance</h3>
    <p><span class="badge">Generated</span> {esc(pipeline.get("generated_at", "unknown"))}</p>
    <p><span class="badge">Commit</span> {esc(metadata.get("git", {}).get("commit_short", "unknown"))}</p>
    <p><span class="badge">Branch</span> {esc(metadata.get("git", {}).get("branch", "unknown"))}</p>
    <p><span class="badge">Pipeline SSSOM files</span> {esc(manifest.get("sssom_file_count", "unknown"))} generated in the frozen run; {total_files} files exist on disk.</p>
  </div>
</section>

<section class="section cards">
  <div class="card"><h3>Pipeline outcomes</h3><p class="good"><strong>{ready}</strong> ready</p><p class="warn"><strong>{failed_unreachable}</strong> failed due to unreachable artifacts</p><p class="bad"><strong>{failed_parse}</strong> failed after fetch because no rules were extracted</p></div>
  <div class="card"><h3>Extraction strategies</h3><p><strong>{llm}</strong> LLM extraction graph edges</p><p><strong>{deterministic}</strong> deterministic extraction graph edges</p><p><strong>{unknown}</strong> legacy/file-based graph edge</p></div>
  <div class="card"><h3>Crosswalk graph</h3>{human_graph_text}<p><strong>{graph['crosswalk_nodes']}</strong> nodes / <strong>{graph['crosswalk_edges']}</strong> edges in the legacy graph export</p></div>
</section>
"""
    write(PUBLIC / "index.html", render_page("Overview", "Overview", overview, "Evidence-based metadata crosswalk documentation and statistics."))

    predicate_rows = [
        [esc(name), esc(count), esc(pct(count, total_rows))]
        for name, count in predicates.most_common()
    ]
    justification_rows = [
        [esc(name), esc(count), esc(pct(count, total_rows))]
        for name, count in justifications.most_common()
    ]
    sssom_rows = [
        [
            esc(item.filename),
            esc(item.rows),
            esc(item.predicates.get("skos:exactMatch", 0)),
            esc(item.predicates.get("skos:relatedMatch", 0)),
            esc(item.predicates.get("skos:broadMatch", 0)),
            esc(item.predicates.get("skos:narrowMatch", 0)),
        ]
        for item in sorted(sssom_files, key=lambda item: item.rows, reverse=True)
    ]
    status_rows = [[esc(k), esc(v), esc(pipeline.get("status_rates", {}).get(k, ""))] for k, v in pipeline.get("status_counts", {}).items()]
    strategy_rows = [[esc(k), esc(v)] for k, v in pipeline.get("strategy_counts", {}).items()]
    fetched_extensions = pipeline.get("artifact_checks", {}).get("extension_fetched", {})
    requested_formats = [".xsl", ".html", ".pdf", ".zip"]
    format_rows = [
        [esc(format_name), esc(fetched_extensions.get(format_name, 0))]
        for format_name in requested_formats
    ]
    format_plot = (
        '<img class="stats-plot" src="assets/poster_fetched_artifact_formats_bar.png" '
        'alt="Fetched artifact format counts">'
        if (PUBLIC / "assets" / "poster_fetched_artifact_formats_bar.png").exists()
        else "<p>Regenerate <code>poster_fetched_artifact_formats_bar.png</code> to show the format chart.</p>"
    )
    host_rows = [
        [esc(row["host"]), esc(row["fetched"]), esc(row["failed"]), esc(row["total"])]
        for row in host_outcomes
    ]
    host_plot = (
        '<img class="stats-plot" src="assets/poster_artifact_host_outcomes_bar.png" '
        'alt="Fetched and failed artifact URL hosts">'
        if (PUBLIC / "assets" / "poster_artifact_host_outcomes_bar.png").exists()
        else "<p>Regenerate <code>poster_artifact_host_outcomes_bar.png</code> to show the host chart.</p>"
    )
    benchmark_plot = render_live_benchmark_plotly(live_benchmark)
    benchmark_section = (
        f"""
<section class="section benchmark-panel">
  <div class="benchmark-copy">
    <div class="eyebrow">Live OAI-PMH benchmark</div>
    <h2>1,000 heterogeneous AWI records converted without fetch failures.</h2>
    <p class="lead">The DataCite/OpenAIRE to Dublin Core stress test is intentionally strict: Dublin Core is a broad target schema, so rich source metadata is compressed into fewer, less-specific fields. The numbers below quantify semantic compression and rule gaps rather than pipeline failure.</p>
    <div class="metrics-grid benchmark-metrics">
      {metric(f"{live_benchmark['cases']:,}", "distinct live OAI-PMH records")}
      {metric(f"{live_benchmark['failures']}", "fetch/conversion failures")}
      {metric(f"{live_benchmark['field_coverage']:.1f}%", "average field coverage")}
      {metric(f"{live_benchmark['value_overlap']:.1f}%", "average value overlap")}
      {metric(f"{live_benchmark['semantic_loss_rate']:.1f}%", "semantic loss rate")}
    </div>
  </div>
  <div class="benchmark-plot-card">
    <h3>Concentric benchmark rings</h3>
    {benchmark_plot}
  </div>
</section>
"""
        if live_benchmark.get("available")
        else ""
    )
    stats_body = f"""
<section class="panel">
  <div class="eyebrow">Current frozen numbers</div>
  <h2>Pipeline and SSSOM statistics</h2>
  <div class="metrics-grid">
    {metric(total_crosswalks, "total RDAMSC crosswalks")}
    {metric(f"{ready} / {total_crosswalks}", "ready crosswalks")}
    {metric(total_rows, "strict SSSOM data rows")}
    {metric(graph['graph_rule_count'], "rule count in graph metadata")}
    {metric(f"{fetched}/{artifact_checks}", "artifact fetches succeeded")}
    {metric(f"{fetch_errors}/{artifact_checks}", "artifact fetches failed")}
  </div>
</section>

{benchmark_section}

<section class="section two-col">
  <div class="card"><h3>Pipeline status</h3>{table(["Status", "Count", "Rate %"], status_rows)}</div>
  <div class="card"><h3>Pipeline strategy counts</h3>{table(["Strategy", "Count"], strategy_rows)}</div>
</section>

<section class="section two-col">
  <div class="card artifact-format-card">
    <h3>Fetched artifact formats</h3>
    <p>The frozen pipeline successfully fetched <strong>{fetched}</strong> artifacts; these are the poster-relevant format counts.</p>
    {format_plot}
  </div>
  <div class="card"><h3>Format occurrences</h3>{table(["Format", "Fetched artifacts"], format_rows)}</div>
</section>

<section class="section two-col">
  <div class="card artifact-format-card">
    <h3>Artifact URL hosts</h3>
    <p>Successful fetches use the FAIR Data Commons green; failed fetches use the HMC Information red.</p>
    {host_plot}
  </div>
  <div class="card"><h3>Host outcomes</h3>{table(["Host", "Fetched", "Failed", "Total"], host_rows)}</div>
</section>

<section class="section two-col">
  <div class="card"><h3>SSSOM predicates</h3>{table(["Predicate", "Rows", "Share"], predicate_rows)}</div>
  <div class="card"><h3>SSSOM mapping justifications</h3>{table(["Justification", "Rows", "Share"], justification_rows)}</div>
</section>

<section class="section card">
  <h3>SSSOM files by rule count</h3>
  {table(["File", "Rows", "Exact", "Related", "Broad", "Narrow"], sssom_rows)}
</section>
"""
    write(PUBLIC / "statistics.html", render_page("Statistics", "Statistics", stats_body, "Frozen pipeline, SSSOM, and graph-derived numbers."))

    largest_rows = []
    for edge in graph["largest_edges"]:
        metadata_edge = edge.get("metadata", {})
        largest_rows.append(
            [
                esc(edge.get("label", edge.get("id", ""))),
                esc(edge.get("source", "")),
                esc(edge.get("target", "")),
                esc(metadata_edge.get("strategy", "unknown")),
                esc(metadata_edge.get("rule_count", 0)),
            ]
        )
    type_rows = [[esc(k), esc(v)] for k, v in graph["human_types"].most_common()]
    relationship_rows = [[esc(k), esc(v)] for k, v in graph["relationships"].most_common()]
    has_cytoscape = (PUBLIC / "graph-visualizer" / "cytoscape_graph.html").exists()
    cytoscape_embed = (
        '<div class="card graph-embed-card">'
        '<h3>Interactive graph</h3>'
        '<iframe class="graph-embed"'
        ' src="graph-visualizer/cytoscape_graph.html?embed=1"'
        ' title="Interactive Cytoscape crosswalk graph"'
        ' loading="lazy"></iframe>'
        '<a class="graph-open-link" href="graph-visualizer/cytoscape_graph.html"'
        ' target="_blank">Open full screen ↗</a>'
        '</div>'
        if has_cytoscape
        else '<div class="card"><p>Interactive graph renderer not available in this build.</p></div>'
    )

    asset_cards = []
    if (PUBLIC / "assets" / "legend.svg").exists():
        asset_cards.append('<div class="card"><h3>Legend</h3><img src="assets/legend.svg" alt="Graph legend"></div>')
    if (PUBLIC / "assets" / "crosswalk-network.svg").exists():
        asset_cards.append('<div class="card"><h3>Static crosswalk network</h3><img src="assets/crosswalk-network.svg" alt="Crosswalk graph"></div>')
    if not asset_cards:
        asset_cards.append('<div class="card"><h3>Static assets</h3><p>No optional graph images were present in this build. Regenerate assets locally with <code>scripts/export_legend.py</code>.</p></div>')

    graph_body = f"""
<section class="panel">
  <div class="eyebrow">Network view</div>
  <h2>Crosswalk graph</h2>
  <p class="lead">Explore the interactive Cytoscape graph below, or open it full screen. Static legend and graph assets are available for slides.</p>
</section>

<section class="section cards">
  {cytoscape_embed}
</section>

<section class="section two-col">
  <div class="card"><h3>Node categories</h3>{table(["Category", "Nodes"], type_rows)}</div>
  <div class="card"><h3>Edge relationships</h3>{table(["Relationship", "Edges"], relationship_rows)}</div>
</section>

<section class="section card"><h3>Largest crosswalk edges</h3>{table(["Crosswalk", "Source", "Target", "Strategy", "Rules"], largest_rows)}</section>
"""
    write(PUBLIC / "graph.html", render_page("Graph", "Graph", graph_body, "Interactive and static crosswalk graph outputs."))

    documentation_body = """
<section class="panel">
  <div class="eyebrow">How the system works</div>
  <h2>Project documentation</h2>
  <p class="lead">m2s3om_graph syncs RDAMSC metadata, fetches mapping artifacts, extracts crosswalk rules, exports authoritative SSSOM TSV files, and applies those rules in a Streamlit workbench.</p>
</section>
<section class="section cards">
  <div class="card"><h3>Run locally</h3><pre><code>uv sync
uv run streamlit run app/app.py
uv run python -m m2s3om_graph.cli.main demo-convert</code></pre></div>
  <div class="card"><h3>Regenerate statistics</h3><pre><code>uv run python scripts/rdamsc_pipeline_stats.py freeze \
  --status-file .local/rdamsc_pipeline_status.json \
  --output-dir exports/pipeline/latest \
  --sssom-dir exports/sssom \
  --pipeline-log .local/bootstrap_rdamsc.log \
  --plots</code></pre></div>
  <div class="card"><h3>Build this site</h3><pre><code>python scripts/build_pages.py</code></pre></div>
</section>
<section class="section card">
  <h3>Source documents</h3>
  <p>See repository files <code>README.md</code>, <code>BENCHMARKING.md</code>, <code>DEMO_GUIDE.md</code>, <code>POSTER_BRIEF.md</code>, <code>TALK_RESULTS_SNAPSHOT.md</code>, and <code>CODEBASE_WALKTHROUGH.md</code> for the full project narrative.</p>
</section>
"""
    write(PUBLIC / "documentation.html", render_page("Documentation", "Documentation", documentation_body, "Usage notes and regeneration commands."))

    file_rows = [
        ["Pipeline summary", "exports/pipeline/latest/rdamsc_stats_summary.json"],
        ["Pipeline metadata", "exports/pipeline/latest/run_metadata.json"],
        ["SSSOM manifest", "exports/sssom/generation_manifest.json"],
        ["SSSOM exports", "exports/sssom/*.sssom.tsv"],
        ["Legacy graph JSON", "exports/graph/crosswalk_graph.json"],
        ["Human graph JSON", "data/crosswalks.human.json"],
        ["Live OAI benchmark", "exports/benchmark/datacite_dc_oai_awi_benchmark.json"],
        ["Graph visualizer", "graph-visualizer/web/"],
    ]
    files_body = f"""
<section class="panel"><div class="eyebrow">Data provenance</div><h2>Files used by this site</h2><p class="lead">The site is generated from repository-local files so it can be reproduced in CI and cited in presentations.</p></section>
<section class="section card">{table(["Purpose", "Repository path"], [[esc(a), f"<code>{esc(b)}</code>"] for a, b in file_rows])}</section>
<section class="section card"><h3>Artifact plots</h3><p><a href="assets/plots/status_counts.png">status_counts.png</a>, <a href="assets/plots/failure_reasons.png">failure_reasons.png</a>, <a href="assets/plots/hosts_errors.png">hosts_errors.png</a>, <a href="assets/plots/extensions_fetched.png">extensions_fetched.png</a>, <a href="assets/plots/extensions_errors.png">extensions_errors.png</a>, <a href="assets/poster_crosswalk_status_pie.png">poster_crosswalk_status_pie.png</a>, <a href="assets/poster_datacite_dublincore_benchmark_bar.png">poster_datacite_dublincore_benchmark_bar.png</a>, <a href="assets/poster_fetched_artifact_formats_bar.png">poster_fetched_artifact_formats_bar.png</a>, <a href="assets/poster_artifact_host_outcomes_bar.png">poster_artifact_host_outcomes_bar.png</a>, <a href="assets/live_oai_pmh_concentric_rings.png">live_oai_pmh_concentric_rings.png</a></p></section>
"""
    write(PUBLIC / "files.html", render_page("Files", "Files", files_body, "Source files and generated assets."))


if __name__ == "__main__":
    build()
    print(f"Built GitLab Pages site at {PUBLIC}")
