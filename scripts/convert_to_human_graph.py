#!/usr/bin/env python3
"""Convert M²S³OM crosswalk_graph.json to graphkit human.json format.

Usage:
    uv run python scripts/convert_to_human_graph.py \
        --input exports/graph/crosswalk_graph.json \
        --output data/crosswalks.human.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


@dataclass
class Node:
    sssom_id: str
    label: str
    rule_count: int = 0


@dataclass
class Crosswalk:
    id: str
    source: str
    target: str
    rule_count: int
    strategy: str  # deterministic | llm | unknown
    edge_id: str


@dataclass
class CrosswalkData:
    standards: dict[str, Node] = field(default_factory=dict)
    crosswalks: list[Crosswalk] = field(default_factory=list)


def load_crosswalks(data: dict) -> CrosswalkData:
    standards: dict[str, Node] = {}
    for n in data["nodes"]:
        s = n["id"]
        standards[s] = Node(sssom_id=s, label=n.get("label") or s, rule_count=0)

    crosswalks: list[Crosswalk] = []
    for e in data["edges"]:
        c = Crosswalk(
            id=e["id"],
            source=e["source"],
            target=e["target"],
            rule_count=e["metadata"]["rule_count"],
            strategy=e["metadata"]["strategy"],
            edge_id=e["id"],
        )
        crosswalks.append(c)
        if c.source in standards:
            standards[c.source].rule_count += c.rule_count
        if c.target in standards:
            standards[c.target].rule_count += c.rule_count

    return CrosswalkData(standards=standards, crosswalks=crosswalks)


def to_human_graph(data: CrosswalkData) -> dict:
    nodes: list[dict] = []
    edge_attributes: dict[str, dict] = {}
    node_attributes: dict[str, dict] = {}

    strategy_labels = {
        "deterministic": "Deterministic extraction",
        "llm": "LLM extraction",
        "unknown": "Unknown strategy",
    }
    for stratum, attr in {
        "deterministic": {"color": "#50C878"},
        "llm": {"color": "#FFB84D"},
        "unknown": {"color": "#95A5A6"},
    }.items():
        k = f"strategy_{stratum}"
        edge_attributes[k] = {**attr, "strategy": stratum}

    node_attributes["standard"] = {"color": "#4A90E2"}

    for s in sorted(data.standards):
        standard = data.standards[s]
        nodes.append({
            "id": s,
            "type": "standard",
            "label": standard.label,
            "attrRef": "standard",
        })

    edges: list[dict] = []
    for c in data.crosswalks:
        rel_key = f"strategy_{c.strategy}"
        rel_label = strategy_labels.get(c.strategy, f"{c.strategy} (edge)")
        edges.append({
            "source": c.source,
            "target": c.target,
            "relationship": rel_label,
            "attrRef": rel_key,
        })

    return {
        "meta": {
            "schemaVersion": "1",
            "title": "M²S³OM Crosswalk Network",
            "notes": "Graph-derived from SSSOM crosswalk mappings",
            "directed": True,
        },
        "nodes": nodes,
        "edges": edges,
        "nodeAttributes": node_attributes,
        "edgeAttributes": edge_attributes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert M²S³OM crosswalk_graph.json to graphkit human.json"
    )
    ap.add_argument(
        "--input", type=Path, default=None,
        help="Path to crosswalk_graph.json. Default: <repo-root>/exports/graph/crosswalk_graph.json",
    )
    ap.add_argument(
        "--output", type=Path, default=None,
        help="Output path for human.json. Default: <repo-root>/data/crosswalks.human.json",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    in_path = args.input or root / "exports/graph/crosswalk_graph.json"
    out_path = args.output or root / "data/crosswalks.human.json"

    data = load(in_path)
    xw = load_crosswalks(data)
    human = to_human_graph(xw)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(human, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path} ({len(human['nodes'])} nodes, {len(human['edges'])} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
