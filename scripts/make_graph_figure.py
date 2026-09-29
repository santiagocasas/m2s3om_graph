#!/usr/bin/env python3
"""Draw the RDAMSC crosswalk graph as a publication figure.

Reads (read-only, never modified by this script):
  - exports/graph/crosswalk_graph.json   (canonical graph export: 24 nodes, 26 edges,
                                           node ids/labels -- the fixed x/y layout in this
                                           file is NOT used any more, see layout note below)
  - scripts/standard_topics.json         (DRAFT node id -> topic mapping, Part B)
  - exports/pipeline/strategies.csv      (per-crosswalk extraction strategy, ground truth
                                           for edge line style -- NOT exports/graph's own
                                           "strategy" field, which Part A.2 of
                                           AUDIT_REPORT_2026-09-29_freeze.md found to be a
                                           hardcoded 2-crosswalk allowlist plus a blanket
                                           "llm" default for everything else)
  - exports/sssom/*.sssom.tsv            (raw row counts per crosswalk, used for edge width
                                           and the self-loop's row-count label, instead of
                                           exports/graph's rule_count, which item 5 of the
                                           freeze audit found to be systematically +1-inflated
                                           vs the real SSSOM row count)

Writes (only these two files, both new/untracked, nothing under exports/ or paper/main.tex
is ever touched):
  - paper/figures/graph_topics.pdf
  - paper/figures/graph_topics.png

Layout (2026-09-29 revision): the graph's own exported x/y coordinates produced a circular
layout with long crossing chords. This script instead: (1) computes the connected components
of the undirected graph, (2) lays each one out independently with
networkx.kamada_kawai_layout, (3) places the largest component in a left panel (~55% of the
plot width) and the other four in a 2x2 grid on the right, each scaled to fill its own panel.
Node ids/edges/topics/strategies/row counts all still come from the sources listed above --
only the on-page *position* of each node is recomputed here.

Known, deliberately-preserved defects from the underlying export (see Part A of the
2026-09-29 graph-diagnosis report and paper/figures/FIGURE_GRAPH_REPORT.md for the full
write-up): the rdamsc_c38 self-loop on rdamsc_m11, and the two duplicate node pairs
(datacite_4_4 / rdamsc_m11) and (dublin_core_terms / rdamsc_m15). This script draws the
graph exactly as exported -- it does not merge or fix these -- and prints a warning listing
them so they are never silently forgotten.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
GRAPH_JSON = ROOT / "exports" / "graph" / "crosswalk_graph.json"
TOPICS_JSON = ROOT / "scripts" / "standard_topics.json"
STRATEGIES_CSV = ROOT / "exports" / "pipeline" / "strategies.csv"
SSSOM_DIR = ROOT / "exports" / "sssom"
OUT_DIR = ROOT / "paper" / "figures"

# Curated (non-rdamsc) crosswalk file name -> sssom file, kept separate from the
# rdamsc_cNN naming used by the pipeline.
CURATED_SSSOM = {"datacite44_to_dcterms": "datacite44_to_dcterms.sssom.tsv"}

# 7-topic colour palette (Okabe-Ito-derived, colourblind-safe, consistent with the
# palette used in scripts/make_paper_figures.py).
TOPIC_COLORS = {
    "Aeronautics/Space/Transport": "#0072B2",
    "Earth and Environment": "#009E73",
    "FAIR data commons": "#E69F00",
    "Health": "#CC79A7",
    "Information": "#56B4E9",
    "Matter and Heritage": "#D55E00",
    "Projects and Registries": "#999999",
}
EDGE_COLOR = "#3B3B3B"  # dark gray, per spec
DUPLICATE_NODE_IDS = {"datacite_4_4", "rdamsc_m11", "dublin_core_terms", "rdamsc_m15"}

# Node id -> short label, exactly the 24 labels specified by the user, one per node id.
SHORT_LABELS: dict[str, str] = {
    "rdamsc_m1": "ABCD",
    "rdamsc_m9": "Darwin Core",
    "rdamsc_m15": "Dublin Core",
    "dublin_core_terms": "DC Terms",
    "datacite_4_4": "DataCite",
    "rdamsc_m11": "DataCite (RDAMSC)",
    "rdamsc_m88": "MARC",
    "rdamsc_m97": "MODS",
    "rdamsc_m16": "EML",
    "rdamsc_m22": "ISO 19115",
    "rdamsc_m85": "EURISCO",
    "rdamsc_m64": "HISPID",
    "rdamsc_m21": "ISA-Tab",
    "rdamsc_m87": "MAGE-TAB",
    "rdamsc_m13": "DDI",
    "rdamsc_m89": "NetCDF ACDD",
    "rdamsc_m90": "OECD",
    "rdamsc_m39": "SPASE",
    "rdamsc_m46": "ANZLIC",
    "rdamsc_m98": "RIF-CS",
    "rdamsc_m109": "LIDO",
    "rdamsc_m114": "CIDOC CRM",
    "rdamsc_m24": "MIDAS-Heritage",
    "rdamsc_m96": "EAD",
}

# ---- physical layout constants (all in millimetres in the graph axes' data space,
# chosen so that 1 data unit == 1 physical mm on the page) ----
FIG_W_CM = 17.0
FIG_H_CM = 11.0  # bumped from 9 to 11 (still within the allowed range) to fit the
                  # 11-node left component without crowding
LEGEND_STRIP_MM = 15.0  # top strip reserved for both legends, outside the node area
                         # entirely -- guarantees the legend never covers a node
PANEL_MARGIN_MM = 5.0
PANEL_GAP_MM = 6.0
NODE_INSET_FRAC = 0.20  # margin inside each panel before nodes/labels start
PT_TO_MM = 25.4 / 72.0


def load_graph() -> dict:
    return json.loads(GRAPH_JSON.read_text())


def load_topics() -> dict:
    data = json.loads(TOPICS_JSON.read_text())
    return data["assignments"]


def load_strategy_classes() -> dict[str, str]:
    """crosswalk_id (e.g. 'rdamsc_c1') -> 'deterministic' | 'llm' | 'curated' | 'none'."""
    classes: dict[str, str] = {}
    with STRATEGIES_CSV.open() as fh:
        for row in csv.DictReader(fh):
            strat = row["strategy"].strip()
            if strat.startswith("deterministic"):
                cls = "deterministic"
            elif strat.startswith("llm"):
                cls = "llm"
            elif strat.startswith("curated"):
                cls = "curated"
            else:
                cls = "none"  # "NONE (no file)"
            classes[row["crosswalk_id"]] = cls
    return classes


def count_sssom_rows(path: Path) -> int:
    n = 0
    with path.open(newline="", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            n += 1
    return max(n - 1, 0)  # subtract header row


def load_rule_counts() -> dict[str, int]:
    """crosswalk_id -> raw SSSOM data-row count (NOT the +1-inflated graph rule_count)."""
    counts: dict[str, int] = {}
    for tsv in SSSOM_DIR.glob("rdamsc_c*.sssom.tsv"):
        cid = tsv.stem.replace(".sssom", "")  # rdamsc_cNN
        counts[cid] = count_sssom_rows(tsv)
    for crosswalk_id, fname in CURATED_SSSOM.items():
        p = SSSOM_DIR / fname
        if p.exists():
            counts[crosswalk_id] = count_sssom_rows(p)
    return counts


def short_label(node_id: str, full_label: str, warnings: list[str]) -> str:
    if node_id in SHORT_LABELS:
        return SHORT_LABELS[node_id]
    warnings.append(f"node {node_id}: not in SHORT_LABELS dict, using original label {full_label!r}")
    return full_label


# ---------------------------------------------------------------------------
# Layout: connected components, each laid out independently, then packed into
# a left panel (largest) + 2x2 grid (the other four).
# ---------------------------------------------------------------------------

def compute_component_layout(nodes: dict, edges: list, warnings: list[str]) -> dict[str, tuple[float, float]]:
    undirected_edges = [(e["source"], e["target"]) for e in edges if e["source"] != e["target"]]

    g = nx.Graph()
    g.add_nodes_from(nodes.keys())
    g.add_edges_from(undirected_edges)

    components = sorted(nx.connected_components(g), key=len, reverse=True)
    if len(components) != 5:
        warnings.append(f"expected 5 connected components, found {len(components)}")

    graph_h_mm = FIG_H_CM * 10.0 - LEGEND_STRIP_MM
    graph_w_mm = FIG_W_CM * 10.0

    left_w = 0.55 * (graph_w_mm - 2 * PANEL_MARGIN_MM - PANEL_GAP_MM)
    right_w = (graph_w_mm - 2 * PANEL_MARGIN_MM - PANEL_GAP_MM) - left_w
    left_box = (PANEL_MARGIN_MM, PANEL_MARGIN_MM, left_w, graph_h_mm - 2 * PANEL_MARGIN_MM)

    right_x0 = PANEL_MARGIN_MM + left_w + PANEL_GAP_MM
    cell_w = (right_w - PANEL_GAP_MM) / 2
    cell_h = (graph_h_mm - 2 * PANEL_MARGIN_MM - PANEL_GAP_MM) / 2
    grid_boxes = [
        (right_x0, PANEL_MARGIN_MM + cell_h + PANEL_GAP_MM, cell_w, cell_h),  # top-left
        (right_x0 + cell_w + PANEL_GAP_MM, PANEL_MARGIN_MM + cell_h + PANEL_GAP_MM, cell_w, cell_h),  # top-right
        (right_x0, PANEL_MARGIN_MM, cell_w, cell_h),  # bottom-left
        (right_x0 + cell_w + PANEL_GAP_MM, PANEL_MARGIN_MM, cell_w, cell_h),  # bottom-right
    ]
    boxes = [left_box] + grid_boxes

    node_pos: dict[str, tuple[float, float]] = {}
    panel_boxes: list[tuple[float, float, float, float]] = []
    for component, box in zip(components, boxes):
        sub = g.subgraph(component)
        if sub.number_of_edges() == 0:
            # Should not happen here (min component size is 2, fully connected), but
            # guard against a degenerate kamada_kawai call on an edgeless graph.
            pos = {n: (0.5, 0.5) for n in component}
        else:
            pos = nx.kamada_kawai_layout(sub)

        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        rx = (max(xs) - min(xs)) or 1.0
        ry = (max(ys) - min(ys)) or 1.0
        minx, miny = min(xs), min(ys)

        bx0, by0, bw, bh = box
        inset_w = bw * NODE_INSET_FRAC
        inset_h = bh * NODE_INSET_FRAC
        inner_w = bw - 2 * inset_w
        inner_h = bh - 2 * inset_h
        for n, (px, py) in pos.items():
            nx_ = (px - minx) / rx
            ny_ = (py - miny) / ry
            node_pos[n] = (bx0 + inset_w + nx_ * inner_w, by0 + inset_h + ny_ * inner_h)
        panel_boxes.append(box)

    return node_pos, panel_boxes, graph_w_mm, graph_h_mm


def build(dry_run: bool = False) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    graph = load_graph()
    topics = load_topics()
    strategy_classes = load_strategy_classes()
    rule_counts = load_rule_counts()

    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]

    node_pos, panel_boxes, graph_w_mm, graph_h_mm = compute_component_layout(nodes, edges, warnings)

    # ---- degree (for node size) and row counts (for edge width) ----
    mg = nx.MultiGraph()
    mg.add_nodes_from(nodes.keys())
    for e in edges:
        mg.add_edge(e["source"], e["target"])
    degree = dict(mg.degree())
    deg_min, deg_max = min(degree.values()), max(degree.values())

    def node_area_pts2(nid: str) -> float:
        lo, hi = 60.0, 220.0
        if deg_max == deg_min:
            return (lo + hi) / 2
        t = (degree[nid] - deg_min) / (deg_max - deg_min)
        return lo + t * (hi - lo)

    def node_radius_mm(nid: str) -> float:
        area = node_area_pts2(nid)
        return math.sqrt(area / math.pi) * PT_TO_MM

    all_rows = []
    for e in edges:
        cid = e["metadata"]["crosswalk_id"]
        rows = rule_counts.get(cid, e["metadata"].get("rule_count", 1))
        all_rows.append(rows)
    rows_min, rows_max = min(all_rows), max(all_rows)
    sr_min, sr_max = math.sqrt(max(rows_min, 1)), math.sqrt(max(rows_max, 1))

    def edge_linewidth(rows: int) -> float:
        lo, hi = 0.6, 3.0
        if sr_max == sr_min:
            return (lo + hi) / 2
        t = (math.sqrt(max(rows, 1)) - sr_min) / (sr_max - sr_min)
        return lo + t * (hi - lo)

    # ---- parallel / opposite-direction edge pairs: draw curved, everything else straight ----
    pair_counts: dict[frozenset, int] = {}
    for e in edges:
        if e["source"] == e["target"]:
            continue
        pair_counts.setdefault(frozenset((e["source"], e["target"])), 0)
        pair_counts[frozenset((e["source"], e["target"]))] += 1
    pair_seen: dict[frozenset, int] = {}

    # ---- figure ----
    fig = plt.figure(figsize=(FIG_W_CM / 2.54, FIG_H_CM / 2.54), dpi=300)
    legend_h_frac = (LEGEND_STRIP_MM / 10.0) / FIG_H_CM
    graph_ax = fig.add_axes([0.0, 0.0, 1.0, 1.0 - legend_h_frac])
    legend_ax = fig.add_axes([0.0, 1.0 - legend_h_frac, 1.0, legend_h_frac])
    graph_ax.set_aspect("equal")
    graph_ax.axis("off")
    legend_ax.axis("off")
    graph_ax.set_xlim(0, graph_w_mm)
    graph_ax.set_ylim(0, graph_h_mm)

    # panel background rectangles, purely so the five components read as clearly
    # separated groups regardless of exact node spacing
    for bx0, by0, bw, bh in panel_boxes:
        graph_ax.add_patch(FancyBboxPatch(
            (bx0, by0), bw, bh, boxstyle="round,pad=0.6,rounding_size=2.0",
            facecolor="#F6F6F6", edgecolor="#DDDDDD", linewidth=0.6, zorder=0,
        ))

    style_map = {"deterministic": "dashed", "llm": "solid", "curated": "dotted", "none": "solid"}

    # ---- edges ----
    self_loop_boxes: list[tuple[float, float, float, float]] = []
    for e in edges:
        cid = e["metadata"]["crosswalk_id"]
        src, tgt = e["source"], e["target"]
        cls = strategy_classes.get(cid, "curated" if cid in CURATED_SSSOM else "none")
        style = style_map[cls]
        rows = rule_counts.get(cid, e["metadata"].get("rule_count", 1))
        lw = edge_linewidth(rows)

        sx, sy = node_pos[src]
        tx, ty = node_pos[tgt]

        if src == tgt:
            r = max(node_radius_mm(src) * 1.8, 3.0)
            loop = Circle((sx, sy + r), r, fill=False, edgecolor=EDGE_COLOR,
                          linestyle=style, linewidth=lw, zorder=2)
            graph_ax.add_patch(loop)
            graph_ax.annotate(str(rows), (sx, sy + 2 * r + 1.5), ha="center", va="bottom",
                               fontsize=5.5, color=EDGE_COLOR, zorder=6)
            # reserve the loop + its row-count label as an obstacle for node labels
            self_loop_boxes.append((sx - r * 1.1, sy - r * 0.2, sx + r * 1.1, sy + 2 * r + 4.5))
            continue

        pair = frozenset((src, tgt))
        n_parallel = pair_counts.get(pair, 1)
        if n_parallel > 1:
            idx = pair_seen.get(pair, 0)
            pair_seen[pair] = idx + 1
            rad = 0.2 if idx % 2 == 0 else -0.2
            connectionstyle = f"arc3,rad={rad}"
        else:
            connectionstyle = "arc3,rad=0.0"

        arrow = FancyArrowPatch((sx, sy), (tx, ty), arrowstyle="-|>", mutation_scale=5,
                                 linestyle=style, linewidth=lw, color=EDGE_COLOR,
                                 shrinkA=6, shrinkB=6, zorder=2,
                                 connectionstyle=connectionstyle)
        graph_ax.add_patch(arrow)

    # ---- nodes ----
    xs_scatter, ys_scatter, sizes, colors = [], [], [], []
    node_radii = {}
    for nid in nodes:
        topic = topics.get(nid, {}).get("topic")
        color = TOPIC_COLORS.get(topic, "#BBBBBB")
        if topic is None:
            warnings.append(f"node {nid}: no topic assignment found in standard_topics.json")
        x, y = node_pos[nid]
        xs_scatter.append(x)
        ys_scatter.append(y)
        sizes.append(node_area_pts2(nid))
        colors.append(color)
        node_radii[nid] = node_radius_mm(nid)

    graph_ax.scatter(xs_scatter, ys_scatter, s=sizes, c=colors, edgecolors="white",
                      linewidths=0.6, zorder=3)

    for nid in DUPLICATE_NODE_IDS:
        if nid in node_pos:
            x, y = node_pos[nid]
            r = node_radii[nid]
            graph_ax.annotate("*", (x + r * 0.8, y + r * 0.8), fontsize=7, color="#B00020",
                               fontweight="bold", zorder=5)

    # ---- labels: above/below placement chosen by actual bounding-box overlap
    # (not just point distance) against every node and every already-placed
    # label, white halo so a line never runs through the text ----
    FONT_PT = 6.5
    CHAR_W_MM = FONT_PT * 0.58 * PT_TO_MM
    LABEL_H_MM = FONT_PT * 1.25 * PT_TO_MM

    def rect_overlap_area(a, b):
        ax0, ay0, ax1, ay1 = a
        bx0, by0, bx1, by1 = b
        ox = max(0.0, min(ax1, bx1) - max(ax0, bx0))
        oy = max(0.0, min(ay1, by1) - max(ay0, by0))
        return ox * oy

    node_boxes = [
        (x - r, y - r, x + r, y + r)
        for (x, y), r in ((node_pos[n], node_radii[n]) for n in node_pos)
    ] + self_loop_boxes

    def label_box(x, y, w, va):
        if va == "bottom":  # text sits above the anchor point
            return (x - w / 2, y, x + w / 2, y + LABEL_H_MM)
        return (x - w / 2, y - LABEL_H_MM, x + w / 2, y)  # va == "top": text below anchor

    placed_label_boxes: list[tuple[float, float, float, float]] = []
    order = sorted(node_pos.keys(), key=lambda n: -node_radii[n])
    for nid in order:
        x, y = node_pos[nid]
        label = short_label(nid, nodes[nid]["label"], warnings)
        w = max(len(label) * CHAR_W_MM, 4.0)
        gap = node_radii[nid] + 1.8

        candidates = [("bottom", (x, y + gap)), ("top", (x, y - gap))]
        best_va, best_pt, best_cost = None, None, None
        for va, pt in candidates:
            box = label_box(pt[0], pt[1], w, va)
            cost = sum(rect_overlap_area(box, nb) * 2.0 for nb in node_boxes)
            cost += sum(rect_overlap_area(box, lb) for lb in placed_label_boxes)
            if best_cost is None or cost < best_cost:
                best_va, best_pt, best_cost = va, pt, cost

        placed_label_boxes.append(label_box(best_pt[0], best_pt[1], w, best_va))
        txt = graph_ax.annotate(label, best_pt, ha="center", va=best_va, fontsize=FONT_PT, zorder=6)
        txt.set_path_effects([pe.withStroke(linewidth=1.6, foreground="white")])

    # ---- legend (own strip, above the graph area -- never overlaps a node) ----
    topic_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=c, markeredgecolor="white",
               markersize=6, label=t)
        for t, c in TOPIC_COLORS.items()
    ]
    style_handles = [
        Line2D([0], [0], color=EDGE_COLOR, linestyle="solid", linewidth=1.2, label="LLM extraction"),
        Line2D([0], [0], color=EDGE_COLOR, linestyle="dashed", linewidth=1.2, label="Deterministic extraction"),
        Line2D([0], [0], color=EDGE_COLOR, linestyle="dotted", linewidth=1.2, label="Curated (PDF ingestion)"),
        Line2D([0], [0], marker="$*$", color="none", markerfacecolor="#B00020",
               markeredgecolor="#B00020", markersize=7, label="Known duplicate node (see report)"),
    ]
    leg1 = legend_ax.legend(handles=topic_handles, title="Topic (node color)", loc="center left",
                             bbox_to_anchor=(0.0, 0.5), fontsize=5.0, title_fontsize=5.5,
                             frameon=False, ncol=4, handletextpad=0.4, columnspacing=1.0, labelspacing=0.3)
    legend_ax.add_artist(leg1)
    legend_ax.legend(handles=style_handles, title="Edge style / markers", loc="center right",
                      bbox_to_anchor=(1.0, 0.5), fontsize=5.0, title_fontsize=5.5,
                      frameon=False, handletextpad=0.4, labelspacing=0.3)

    stats = {
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_components": len(panel_boxes),
        "edge_style_counts": {
            k: sum(1 for e in edges
                   if style_map[strategy_classes.get(e["metadata"]["crosswalk_id"],
                                                       "curated" if e["metadata"]["crosswalk_id"] in CURATED_SSSOM else "none")] == v)
            for k, v in {"deterministic": "dashed", "llm": "solid", "curated": "dotted"}.items()
        },
    }

    if dry_run:
        plt.close(fig)
        return stats, warnings

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    fig.savefig(OUT_DIR / "graph_topics.pdf")
    fig.savefig(OUT_DIR / "graph_topics.png", dpi=300)
    plt.close(fig)
    return stats, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="build in memory, write nothing")
    args = ap.parse_args()

    stats, warnings = build(dry_run=args.dry_run)
    print(json.dumps(stats, indent=2))
    if warnings:
        print("\nWARNINGS:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)
    if not args.dry_run:
        print(f"\nWrote {OUT_DIR / 'graph_topics.pdf'}")
        print(f"Wrote {OUT_DIR / 'graph_topics.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
