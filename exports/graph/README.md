# Crosswalk Graph Visualization

Interactive visualization of the M²S³OM-graph metadata crosswalk network using sigma.js.

## Quick Start

### Option 1: Python HTTP Server (Recommended)

```bash
# From project root
uv run python scripts/serve_graph.py
```

This will:
1. Start a local HTTP server on port 8000
2. Automatically open http://localhost:8000 in your browser
3. Display the interactive graph

### Option 2: Direct File Open

Open `index.html` directly in your browser:

```bash
# From project root
firefox exports/graph/index.html
# or
chrome exports/graph/index.html
```

**Note:** Some browsers may block loading `crosswalk_graph.json` due to CORS restrictions when opening files directly. Use Option 1 if this happens.

## Regenerate Graph Data

If you update SSSOM files, regenerate the graph data:

```bash
uv run python scripts/export_graph.py
```

This reads all `.sssom.tsv` files from `exports/sssom/` and generates `crosswalk_graph.json`.

## Graph Features

### Nodes (Standards)
- **Size**: Proportional to total rule participation (larger = more crosswalks)
- **Color**: Blue (#4A90E2) for all standards
- **Label**: Human-readable standard name (e.g., "DataCite 4.4", "Dublin Core")

### Edges (Crosswalks)
- **Thickness**: Proportional to number of mapping rules
- **Color**:
  - 🟢 **Green (#50C878)**: Deterministic extraction (e.g., rdamsc_c36, rdamsc_c38)
  - 🟠 **Orange (#FFB84D)**: LLM extraction (via Blablador)
  - ⚪ **Gray (#95A5A6)**: Unknown strategy

### Interactions

- **Click node**: Show standard details + connected standards
- **Click edge**: Show crosswalk details (name, rule count, extraction strategy, source doc)
- **Click empty space**: Deselect and hide info panel
- **Drag**: Pan the graph
- **Scroll**: Zoom in/out
- **Reset View button**: Return camera to initial position
- **Toggle Labels button**: Show/hide node labels

## Current Statistics

As of latest export:
- **22 standards** (metadata schemas)
- **24 crosswalks** (mapping specifications)
- **~1,280 total mapping rules**
- **2 deterministic extractions** (10%)
- **21 LLM extractions** (88%)

## File Structure

```
exports/graph/
├── index.html              # Interactive visualization (sigma.js)
├── crosswalk_graph.json    # Graph data (nodes + edges)
└── README.md              # This file
```

## Technology Stack

- **sigma.js v3.0**: WebGL-based graph rendering
- **graphology**: Graph data structure library
- **Pure JavaScript**: No build step required

## Demo Workflow

### For Conference Presentation:

1. **Open graph** (Option 1 above)
2. **Show big picture**: "Here are all 22 standards we've mapped, with 24 crosswalks extracted from heterogeneous sources"
3. **Click green edge**: "This is rdamsc_c38 - 160 rules extracted deterministically from a well-structured XSL file"
4. **Click orange edge**: "This crosswalk required LLM extraction - our hybrid pipeline fell back to Blablador when deterministic parsing failed"
5. **Click large node** (e.g., Dublin Core, MARC): "Hub standards with many connections - enabling transitive conversion paths"
6. **Switch to Streamlit**: "Now let's see one of these crosswalks in action..."

### Integration with Streamlit Demo:

1. Graph → Show ecosystem (standards as nodes)
2. Streamlit → Browse specific crosswalk rules (Tab 1)
3. Streamlit → Live conversion demo (Tab 3: HZI record → DataCite)
4. Back to Graph → Highlight the conversion path

## Troubleshooting

**Graph doesn't load:**
- Check browser console for errors
- Verify `crosswalk_graph.json` exists
- Use Python HTTP server (Option 1) instead of direct file open

**Node labels overlap:**
- Click "Toggle Labels" to hide labels temporarily
- Zoom in to specific region of interest
- Drag nodes manually to rearrange (they won't snap back)

**Performance issues:**
- Graph should render smoothly with 22 nodes + 24 edges
- If slow, disable labels or reduce browser zoom

## Customization

Edit `scripts/export_graph.py` to customize:
- Node colors (e.g., color by standard family)
- Edge colors (e.g., add gradient for confidence scores)
- Node sizes (current: based on rule participation)
- Layout algorithm (current: circular arrangement)

For advanced layouts, consider integrating:
- Force-directed layout (Graphology's FA2 algorithm)
- Hierarchical layout (by standard category)
- Custom positioning based on semantic similarity
