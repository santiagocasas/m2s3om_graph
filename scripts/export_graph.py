#!/usr/bin/env python3
"""Export crosswalk graph data from SSSOM files to JSON for sigma.js visualization.

Reads all SSSOM files in exports/sssom/ and creates a graph with:
- Nodes: metadata standards
- Edges: crosswalks with rule counts and metadata
"""

import json
import re
from pathlib import Path
from collections import defaultdict

import yaml


def parse_sssom_metadata(path: Path) -> dict:
    """Extract YAML metadata header from SSSOM file."""
    header_lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        header_lines.append(line[1:])
    
    if not header_lines:
        return {}
    
    loaded = yaml.safe_load("\n".join(header_lines))
    return loaded if isinstance(loaded, dict) else {}


def count_sssom_rules(path: Path) -> int:
    """Count number of data lines (non-header, non-empty) in SSSOM file."""
    count = 0
    in_data = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            in_data = True
        if in_data and line.strip() and not line.startswith("subject_id"):
            count += 1
    return count


def extract_standard_info(curie_map: dict, key: str) -> tuple[str, str]:
    """Extract standard ID and name from CURIE map.
    
    Returns: (standard_id, standard_name)
    """
    if not isinstance(curie_map, dict):
        return (key, key)
    
    raw = curie_map.get(key, "")
    if not isinstance(raw, str):
        return (key, key)
    
    # URL format: https://m2s3om_graph.local/datacite44/
    trimmed = raw.rstrip("/")
    standard_id = trimmed.rsplit("/", 1)[-1] or key
    
    # Try to make a human-readable name
    # Example: datacite44 -> DataCite 4.4
    name_parts = re.findall(r'[A-Za-z]+|\d+', standard_id)
    if len(name_parts) >= 2:
        base = name_parts[0].title()
        version = ".".join(name_parts[1:])
        standard_name = f"{base} {version}"
    else:
        standard_name = standard_id.replace("_", " ").replace("-", " ").title()
    
    return (standard_id, standard_name)


def parse_description(description: str) -> tuple[str, str, str]:
    """Parse mapping_set_description to extract crosswalk name and standard names.
    
    Format: "CrosswalkName (SourceStandard -> TargetStandard)"
    Returns: (crosswalk_name, source_name, target_name)
    """
    pattern = re.compile(r"^(?P<crosswalk>.*?)\s*\((?P<source>.*?)\s*->\s*(?P<target>.*?)\)$")
    match = pattern.match(description.strip())
    
    if match:
        return (
            match.group("crosswalk").strip(),
            match.group("source").strip(),
            match.group("target").strip(),
        )
    
    return (description or "Unknown Crosswalk", "Source", "Target")


def determine_extraction_strategy(crosswalk_id: str, metadata: dict) -> str:
    """Determine if crosswalk was extracted via deterministic or LLM method.
    
    Known deterministic crosswalks: rdamsc_c36, rdamsc_c38
    """
    # Known deterministic successes from TALK_RESULTS_SNAPSHOT.md
    if crosswalk_id in ["rdamsc_c36", "rdamsc_c38"]:
        return "deterministic"
    
    # Check for LLM-related notes in metadata
    doc_uri = metadata.get("mapping_set_source", "")
    if "llm" in str(metadata).lower():
        return "llm"
    
    # Default assumption for rdamsc crosswalks
    if crosswalk_id.startswith("rdamsc_"):
        return "llm"
    
    return "unknown"


def export_graph_data(sssom_dir: Path, output_path: Path) -> dict:
    """Export graph data from SSSOM files.
    
    Returns: {
        "nodes": [{"id": str, "label": str, "size": int, "color": str}, ...],
        "edges": [{"id": str, "source": str, "target": str, "size": int, "label": str, "color": str, "metadata": dict}, ...]
    }
    """
    nodes_dict = {}  # standard_id -> node data
    edges_list = []
    standard_rule_counts = defaultdict(int)  # standard_id -> total rules
    
    for sssom_file in sorted(sssom_dir.glob("*.sssom.tsv")):
        metadata = parse_sssom_metadata(sssom_file)
        
        # Extract crosswalk ID
        mapping_set_id = metadata.get("mapping_set_id", "")
        if not mapping_set_id or ":" not in mapping_set_id:
            continue
        
        crosswalk_id = mapping_set_id.split(":", 1)[1]
        
        # Extract standard info
        curie_map = metadata.get("curie_map", {})
        source_id, source_name = extract_standard_info(curie_map, "src")
        target_id, target_name = extract_standard_info(curie_map, "dst")
        
        # Override with description if available
        description = metadata.get("mapping_set_description", "")
        if description:
            crosswalk_name, desc_source, desc_target = parse_description(description)
            if desc_source != "Source":
                source_name = desc_source
            if desc_target != "Target":
                target_name = desc_target
        else:
            crosswalk_name = crosswalk_id
        
        # Count rules
        rule_count = count_sssom_rules(sssom_file)
        
        # Update node data
        if source_id not in nodes_dict:
            nodes_dict[source_id] = {
                "id": source_id,
                "label": source_name,
                "size": 10,
                "color": "#4A90E2",
                "x": 0,
                "y": 0,
            }
        
        if target_id not in nodes_dict:
            nodes_dict[target_id] = {
                "id": target_id,
                "label": target_name,
                "size": 10,
                "color": "#4A90E2",
                "x": 0,
                "y": 0,
            }
        
        # Track rule counts for node sizing
        standard_rule_counts[source_id] += rule_count
        standard_rule_counts[target_id] += rule_count
        
        # Determine extraction strategy
        strategy = determine_extraction_strategy(crosswalk_id, metadata)
        
        # Edge color based on strategy
        edge_color = {
            "deterministic": "#50C878",  # Green
            "llm": "#FFB84D",  # Orange
            "unknown": "#95A5A6",  # Gray
        }.get(strategy, "#95A5A6")
        
        # Create edge
        edge = {
            "id": f"{source_id}-{target_id}-{crosswalk_id}",
            "source": source_id,
            "target": target_id,
            "size": max(1, rule_count / 20),  # Scale edge thickness
            "label": f"{rule_count} rules",
            "color": edge_color,
            "metadata": {
                "crosswalk_id": crosswalk_id,
                "crosswalk_name": crosswalk_name,
                "rule_count": rule_count,
                "strategy": strategy,
                "source_doc": metadata.get("mapping_set_source", ""),
                "version": metadata.get("mapping_set_version", "unknown"),
            }
        }
        
        edges_list.append(edge)
    
    # Update node sizes based on total rule participation
    max_rules = max(standard_rule_counts.values()) if standard_rule_counts else 1
    for node_id, node_data in nodes_dict.items():
        rule_count = standard_rule_counts.get(node_id, 0)
        # Size: 15-50 based on rule participation
        node_data["size"] = 15 + (35 * rule_count / max_rules)
    
    # Apply force-directed layout approximation (circular arrangement)
    import math
    num_nodes = len(nodes_dict)
    for i, (node_id, node_data) in enumerate(sorted(nodes_dict.items())):
        angle = 2 * math.pi * i / num_nodes
        radius = 300
        node_data["x"] = radius * math.cos(angle)
        node_data["y"] = radius * math.sin(angle)
    
    graph_data = {
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
    }
    
    # Write to output file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")
    
    return graph_data


def main():
    """Export graph data from SSSOM files."""
    project_root = Path(__file__).resolve().parents[1]
    sssom_dir = project_root / "exports" / "sssom"
    output_path = project_root / "exports" / "graph" / "crosswalk_graph.json"
    
    print(f"Reading SSSOM files from: {sssom_dir}")
    graph_data = export_graph_data(sssom_dir, output_path)
    
    print(f"\n✓ Graph data exported to: {output_path}")
    print(f"  Nodes (standards): {len(graph_data['nodes'])}")
    print(f"  Edges (crosswalks): {len(graph_data['edges'])}")
    
    # Print summary
    print("\nStandards in graph:")
    for node in sorted(graph_data["nodes"], key=lambda n: n["label"]):
        print(f"  - {node['label']} (id: {node['id']}, size: {node['size']:.1f})")
    
    print("\nCrosswalks:")
    deterministic = sum(1 for e in graph_data["edges"] if e["metadata"]["strategy"] == "deterministic")
    llm = sum(1 for e in graph_data["edges"] if e["metadata"]["strategy"] == "llm")
    print(f"  Deterministic: {deterministic}")
    print(f"  LLM: {llm}")
    print(f"  Unknown: {len(graph_data['edges']) - deterministic - llm}")


if __name__ == "__main__":
    main()
