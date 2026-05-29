#!/usr/bin/env python3
"""Export a standalone legend figure for the M2S3OM crosswalk graph.

Reads node kind/color and edge strategy/color directly from the graphology JSON
so the legend stays in sync with the graph data automatically.

Usage:
    uv run python scripts/export_legend.py
    uv run python scripts/export_legend.py --output exports/legend.svg
    uv run python scripts/export_legend.py --output exports/legend.png --dpi 300
    uv run python scripts/export_legend.py --graph graphs/crosswalks.graphology.json
"""

import argparse
import json
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def load_legend_data(graph_path: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str, str]]]:
    """Return (node_kinds, edge_types) from a graphology JSON file.

    node_kinds : list of (label, hex_color) sorted alphabetically
    edge_types : list of (label, hex_color, line_style)
    """
    with open(graph_path, encoding="utf-8") as f:
        data = json.load(f)

    # Collect node kinds → pick most-common color per kind
    kind_colors: dict[str, dict[str, int]] = {}
    for node in data.get("nodes", []):
        attrs = node.get("attributes", {})
        kind = attrs.get("kind") or "(unknown)"
        color = attrs.get("color") or "#64748b"
        kind_colors.setdefault(kind, {})
        kind_colors[kind][color] = kind_colors[kind].get(color, 0) + 1

    node_kinds = sorted(
        [
            (kind, max(counts, key=counts.__getitem__))
            for kind, counts in kind_colors.items()
        ],
        key=lambda x: x[0],
    )

    # Collect edge strategies → deduplicate
    seen: dict[str, tuple[str, str]] = {}  # strategy -> (relationship label, color)
    for edge in data.get("edges", []):
        attrs = edge.get("attributes", {})
        strategy = attrs.get("strategy") or "unknown"
        rel = attrs.get("relationship") or strategy.replace("_", " ").title()
        color = attrs.get("color") or "#9ca3af"
        if strategy not in seen:
            seen[strategy] = (rel, color)

    # Fixed display order: deterministic first, then llm, then rest
    order = ["deterministic", "llm"]
    ordered_strategies = order + [s for s in seen if s not in order]
    edge_types = [
        (seen[s][0], seen[s][1], "--" if s == "deterministic" else "-")
        for s in ordered_strategies
        if s in seen
    ]

    return node_kinds, edge_types


def build_legend_figure(
    node_kinds: list[tuple[str, str]],
    edge_types: list[tuple[str, str, str]],
    title: str = "Graph Legend",
    node_size: float = 12,
    font_size: float = 11,
) -> plt.Figure:
    """Build and return a tight legend Figure."""

    handles: list = []

    # ── Node kinds ──────────────────────────────────────────────────────────
    handles.append(
        mpatches.Patch(color="none", label="Node categories")
    )
    for label, color in node_kinds:
        handles.append(
            mpatches.Patch(
                facecolor=color,
                edgecolor="#ffffff",
                linewidth=0.8,
                label=label,
            )
        )

    # Spacer
    handles.append(mpatches.Patch(color="none", label=""))

    # ── Edge types ───────────────────────────────────────────────────────────
    handles.append(
        mpatches.Patch(color="none", label="Edge types")
    )
    for label, color, linestyle in edge_types:
        handles.append(
            Line2D(
                [0], [0],
                color=color,
                linewidth=2.5,
                linestyle=linestyle,
                label=label,
            )
        )

    # ── Figure ───────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(1, 1))  # size overridden by tight layout
    ax.set_axis_off()

    legend = ax.legend(
        handles=handles,
        loc="center",
        frameon=True,
        framealpha=1.0,
        edgecolor="#e5e7eb",
        fancybox=False,
        fontsize=font_size,
        title=title,
        title_fontsize=font_size + 1,
        handlelength=1.6,
        handleheight=1.0,
        handletextpad=0.8,
        labelspacing=0.55,
        borderpad=0.9,
        # Make section headers bold
    )
    legend.get_title().set_fontweight("bold")

    # Bold the section header entries ("Node categories", "Edge types")
    section_labels = {"Node categories", "Edge types"}
    for text in legend.get_texts():
        if text.get_text() in section_labels:
            text.set_fontweight("bold")
            text.set_color("#374151")
        elif text.get_text() == "":
            text.set_fontsize(3)  # spacer: near-invisible

    fig.tight_layout(pad=0.2)

    # Resize figure to fit legend tightly
    renderer = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    bbox = legend.get_window_extent(renderer=renderer)
    pad_px = 16
    w_in = (bbox.width + pad_px * 2) / fig.dpi
    h_in = (bbox.height + pad_px * 2) / fig.dpi
    fig.set_size_inches(w_in, h_in)

    # Re-center the legend after resize
    legend.set_bbox_to_anchor((0.5, 0.5))
    legend._loc = 10  # matplotlib internal: "center"

    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Export M2S3OM graph legend")
    parser.add_argument(
        "--graph",
        default=None,
        help="Path to graphology JSON (default: exports/graph_visualizer_web/graphs/automatic_hm_graph.graphology.json)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: exports/legend.svg + exports/legend.png). "
             "Extension determines format; omit to save both SVG and PNG.",
    )
    parser.add_argument("--dpi", type=int, default=200, help="DPI for raster output (default: 200)")
    parser.add_argument("--title", default="Graph Legend", help="Legend title")
    parser.add_argument("--font-size", type=float, default=11, help="Font size in points (default: 11)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]

    graph_path = Path(args.graph) if args.graph else (
        root / "exports" / "graph_visualizer_web" / "graphs" / "automatic_hm_graph.graphology.json"
    )
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph file not found: {graph_path}")

    node_kinds, edge_types = load_legend_data(graph_path)

    print(f"Node kinds  ({len(node_kinds)}): {[k for k, _ in node_kinds]}")
    print(f"Edge types  ({len(edge_types)}): {[l for l, _, _ in edge_types]}")

    fig = build_legend_figure(
        node_kinds, edge_types,
        title=args.title,
        font_size=args.font_size,
    )

    exports_dir = root / "exports"
    exports_dir.mkdir(exist_ok=True)

    if args.output:
        out = Path(args.output)
        fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
        print(f"Saved: {out}")
    else:
        for ext in ("svg", "png"):
            out = exports_dir / f"legend.{ext}"
            fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
            print(f"Saved: {out}")

    plt.close(fig)


if __name__ == "__main__":
    main()
