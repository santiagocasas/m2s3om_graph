#!/usr/bin/env python3
"""Convert M²S³OM crosswalk_graph.json to graphkit network JSON format.

Usage:
    uv run python scripts/convert_to_crosswalk_network.py \
        --input exports/graph/crosswalk_graph.json \
        --output data/crosswalk_network.json
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_CONFIG = "resources/graph_visualization.yaml"


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_config(path: str | Path) -> dict:
    loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid graph visualization config: {path}")
    return loaded


def resolve_color(config: dict, color_ref: str) -> str:
    palette = config.get("palette", {})
    if isinstance(palette, dict) and color_ref in palette:
        return str(palette[color_ref])
    return color_ref


@dataclass
class Node:
    sssom_id: str
    label: str
    rule_count: int = 0
    aliases: set[str] = field(default_factory=set)


def canonical_standard_id(standard_id: str, config: dict) -> str:
    aliases = config.get("canonical_standards", {})
    if isinstance(aliases, dict):
        return str(aliases.get(standard_id, standard_id))
    return standard_id


def canonical_label(standard_id: str, label: str, config: dict) -> str:
    labels = config.get("canonical_labels", {})
    if isinstance(labels, dict):
        return str(labels.get(standard_id, label))
    return label


def display_label(standard_id: str, label: str, config: dict) -> str:
    labels = config.get("short_labels", {})
    if isinstance(labels, dict) and standard_id in labels:
        return str(labels[standard_id])
    return label.split("(", 1)[0].strip() or label


def topic_for(node_id: str, label: str, config: dict) -> str:
    node_topics = config.get("node_topics", {})
    if isinstance(node_topics, dict) and node_id in node_topics:
        return str(node_topics[node_id])

    label_lower = label.lower()
    if any(term in label_lower for term in ["biological", "darwin", "herbarium"]):
        return "Health"
    if any(term in label_lower for term in ["ecological", "iso 19115", "netcdf", "geographic"]):
        return "Earth and Environment"
    if any(term in label_lower for term in ["cidoc", "lido", "heritage"]):
        return "Matter and Heritage"
    if "spase" in label_lower:
        return "Aeronautics Space Transport"
    if "rif-cs" in label_lower:
        return "Projects and Registries"
    return "Information"


def topic_position(
    topic: str,
    index: int,
    count: int,
    config: dict,
) -> tuple[float, float]:
    topics = config.get("topics", {})
    if not isinstance(topics, dict) or topic not in topics:
        raise KeyError(f"Missing graph visualization topic config: {topic}")
    layout = topics[topic]
    if not isinstance(layout, dict):
        raise ValueError(f"Invalid graph visualization topic config: {topic}")
    if count <= 1:
        return float(layout["x"]), float(layout["y"])

    radius = 48 + min(24, count * 4)
    angle = (index / count) * 6.283185307179586
    return (
        float(layout["x"] + radius * math.cos(angle)),
        float(layout["y"] + radius * math.sin(angle)),
    )


@dataclass
class Crosswalk:
    id: str
    source: str
    target: str
    rule_count: int
    strategy: str  # deterministic | llm | unknown
    edge_id: str
    merged_crosswalk_ids: list[str] = field(default_factory=list)


@dataclass
class CrosswalkData:
    standards: dict[str, Node] = field(default_factory=dict)
    crosswalks: list[Crosswalk] = field(default_factory=list)


def strategy_rank(strategy: str) -> int:
    ranks = {"unknown": 0, "llm": 1, "deterministic": 2}
    return ranks.get(strategy, ranks["unknown"])


def merge_crosswalk(existing: Crosswalk, incoming: Crosswalk) -> None:
    if strategy_rank(incoming.strategy) > strategy_rank(existing.strategy):
        existing.strategy = incoming.strategy

    if incoming.rule_count > existing.rule_count:
        existing.id = incoming.id
        existing.edge_id = incoming.edge_id

    existing.rule_count += incoming.rule_count
    existing.merged_crosswalk_ids.extend(incoming.merged_crosswalk_ids)


def load_crosswalks(data: dict, config: dict) -> CrosswalkData:
    standards: dict[str, Node] = {}
    for n in data["nodes"]:
        original_id = n["id"]
        canonical_id = canonical_standard_id(original_id, config)
        label = canonical_label(canonical_id, n.get("label") or original_id, config)
        if canonical_id not in standards:
            standards[canonical_id] = Node(
                sssom_id=canonical_id,
                label=label,
                rule_count=0,
                aliases=set(),
            )
        if original_id != canonical_id:
            standards[canonical_id].aliases.add(original_id)

    merged_crosswalks: dict[tuple[str, str], Crosswalk] = {}
    for e in data["edges"]:
        c = Crosswalk(
            id=e["id"],
            source=canonical_standard_id(e["source"], config),
            target=canonical_standard_id(e["target"], config),
            rule_count=e["metadata"]["rule_count"],
            strategy=e["metadata"]["strategy"],
            edge_id=e["id"],
            merged_crosswalk_ids=[e["id"]],
        )
        key = (c.source, c.target)
        if key in merged_crosswalks:
            merge_crosswalk(merged_crosswalks[key], c)
        else:
            merged_crosswalks[key] = c

    crosswalks = list(merged_crosswalks.values())
    for c in crosswalks:
        if c.source in standards:
            standards[c.source].rule_count += c.rule_count
        if c.target in standards:
            standards[c.target].rule_count += c.rule_count

    return CrosswalkData(standards=standards, crosswalks=crosswalks)


def to_crosswalk_network(data: CrosswalkData, config: dict) -> dict:
    nodes: list[dict] = []
    edge_attributes: dict[str, dict] = {}
    node_attributes: dict[str, dict] = {}
    max_rule_count = max((c.rule_count for c in data.crosswalks), default=1)

    strategy_labels = {
        "deterministic": "Deterministic extraction",
        "llm": "LLM extraction",
        "unknown": "Unknown strategy",
    }
    strategy_colors = config.get("edge_strategy_colors", {})
    if not isinstance(strategy_colors, dict):
        strategy_colors = {}

    for c in data.crosswalks:
        width = 1.5 + (c.rule_count / max_rule_count) ** 0.5 * 7.5
        color_ref = str(strategy_colors.get(c.strategy, strategy_colors.get("unknown", "#95A5A6")))
        edge_attributes[c.edge_id] = {
            "color": resolve_color(config, color_ref),
            "strategy": c.strategy,
            "rule_count": c.rule_count,
            "size": round(width, 2),
        }
        if len(c.merged_crosswalk_ids) > 1:
            edge_attributes[c.edge_id]["merged_crosswalk_ids"] = sorted(
                c.merged_crosswalk_ids
            )
            edge_attributes[c.edge_id]["merged_count"] = len(c.merged_crosswalk_ids)

    nodes_by_topic: dict[str, list[Node]] = {}
    for standard in data.standards.values():
        topic = topic_for(standard.sssom_id, standard.label, config)
        nodes_by_topic.setdefault(topic, []).append(standard)

    for topic, topic_nodes in nodes_by_topic.items():
        topic_nodes.sort(key=lambda n: n.label)
        for index, standard in enumerate(topic_nodes):
            x, y = topic_position(topic, index, len(topic_nodes), config)
            topic_config = config["topics"][topic]
            color_ref = str(topic_config["color"])
            node_attributes[standard.sssom_id] = {
                "color": resolve_color(config, color_ref),
                "topic": topic,
                "x": round(x, 2),
                "y": round(y, 2),
            }
            if standard.aliases:
                node_attributes[standard.sssom_id]["merged_from"] = sorted(
                    standard.aliases
                )

    for s in sorted(data.standards):
        standard = data.standards[s]
        topic = topic_for(standard.sssom_id, standard.label, config)
        nodes.append({
            "id": s,
            "type": topic,
            "label": display_label(s, standard.label, config),
            "attrRef": s,
        })

    edges: list[dict] = []
    for c in data.crosswalks:
        rel_label = strategy_labels.get(c.strategy, f"{c.strategy} (edge)")
        edges.append({
            "source": c.source,
            "target": c.target,
            "relationship": rel_label,
            "attrRef": c.edge_id,
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
        help="Output path for crosswalk_network.json. Default: <repo-root>/data/crosswalk_network.json",
    )
    ap.add_argument(
        "--config",
        type=Path,
        default=None,
        help=f"Graph visualization YAML config. Default: <repo-root>/{DEFAULT_CONFIG}",
    )
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    in_path = args.input or root / "exports/graph/crosswalk_graph.json"
    out_path = args.output or root / "data/crosswalk_network.json"
    config_path = args.config or root / DEFAULT_CONFIG

    data = load(in_path)
    config = load_config(config_path)
    xw = load_crosswalks(data, config)
    human = to_crosswalk_network(xw, config)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(human, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path} ({len(human['nodes'])} nodes, {len(human['edges'])} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
