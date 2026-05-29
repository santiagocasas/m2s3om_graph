# M²S³OM-graph Conference Demo Guide

Complete walkthrough for presenting the M²S³OM-graph hybrid deterministic-LLM pipeline with graph-grounded interoperability visualization.

## Quick Start Checklist

Before your presentation:

- [ ] Run graph visualization server: `uv run python scripts/serve_graph.py`
- [ ] Start Streamlit app: `uv run streamlit run app/app.py`
- [ ] Open browser tabs:
  - Tab 1: http://localhost:8080 (graph visualization)
  - Tab 2: http://localhost:8501 (Streamlit UI)
- [ ] Test HZI endpoint is working (Streamlit Tab 3 → Repository Browser)
- [ ] Have backup: Take screenshots of graph + successful conversion

---

## Demo Flow (7-10 minutes)

### **Part 1: The Problem (30 seconds)**

> "Scientific metadata interoperability depends on crosswalk specifications - field mappings between standards like DataCite, Dublin Core, MARC. But these mappings are trapped in heterogeneous web artifacts: HTML tables, XSL stylesheets, PDFs, and prose documentation. No existing tool systematically harvests them."

### **Part 2: Graph-Grounded Interoperability (2 minutes)**

**→ Switch to Graph Visualization (localhost:8000)**

> "Here's our solution: M²S³OM-graph extracts these rules and structures them as a knowledge graph."

**Show:**
- Point to stats panel: "**22 metadata standards**, **24 crosswalks**, **~1,280 mapping rules** extracted from the RDAMSC catalog"
- Visual scan: "Each node is a standard, each edge is a crosswalk"

**Click a green edge (rdamsc_c38):**
> "This is our deterministic extraction win: **160 rules** pulled from a well-structured XSL file without any LLM calls. Format-specific parsers handle structured artifacts reproducibly."

**Click an orange edge (any LLM one):**
> "When artifacts resist deterministic parsing - ambiguous PDFs, HTML tables without clear structure - we delegate to **Blablador**, Helmholtz-AI's LLM infrastructure, as a targeted fallback."

**Click a large node (Dublin Core or MARC):**
> "Hub standards enable **transitive path discovery**: if you need to convert Standard A to Standard C but only have A→B and B→C mappings, the graph finds the path automatically."

**Key Message:**
> "This is **graph-grounded interoperability**: standards as nodes, mappings as edges, with full provenance from source documents to executable rules."

---

### **Part 3: Hybrid Deterministic-LLM Pipeline (2 minutes)**

**→ Switch to Streamlit (localhost:8501)**

**Tab 1: Crosswalk Browser**

> "Let's drill into one crosswalk in detail."

**Show:**
- Numbered dropdown: "**24 crosswalks loaded** - immediately visible count"
- Select `1. DataCite-DC-Application-Profile-v1.1 (msc:c1)` or similar
- Rules display: "Here are the individual field mappings"
- Click a rule: "Each rule shows source field, target field, mapping type, confidence, and **evidence snippets** from the original PDF"

**Key Message:**
> "Every mapping rule is linked to the source document chunk - complete traceability from specification to execution."

---

### **Part 4: Live Conversion Demo (3 minutes)**

**Tab 3: Convert One Record**

> "Now let's demonstrate the pipeline in action with a live repository."

**Step 1: Select institution**
- Already defaulted to **HZI (Helmholtz Centre for Infection Research)**
- Show endpoint: `repository.helmholtz-hzi.de`

**Step 2: Discover formats**
- Click "Discover metadata formats"
- Show discovered formats: oai_dc, marc, mods, etc.
- > "Our OAI-PMH integration discovers what formats this repository supports"

**Step 3: Select format & fetch**
- Select **oai_dc** (OAI Dublin Core)
- Use default sample ID or pick from samples
- Click "Fetch source record"
- Show fetched XML

**Step 4: Convert**
- Target format selector (if visible): choose **datacite_xml** or similar
- Click "Convert"
- Show results:
  - ✓ Conversion route (direct or transitive)
  - ✓ Metrics: X rules applied, Y fields mapped, Z unmapped
  - ✓ Output XML (download available)

**Key Message:**
> "End-to-end: **fetch live metadata → apply crosswalk rules → output target format** - all grounded in evidence-based mappings from authoritative sources."

---

### **Part 5: Hybrid Design Findings (1 minute)**

**Back to Graph or stay on Streamlit**

> "Key finding from processing 37 RDAMSC crosswalks:"

**Stats to highlight:**
- ✅ **51% success rate** (19/37 ready)
- ✅ **71% artifact fetch success** (32/45 documents retrieved)
- ✅ **Deterministic-first design**: 2 crosswalks solved without LLM
- ⚠️ **LLM effectiveness**: 20 attempts, 12 successful → **LLMs work as selective recovery tools, not default parsers**

**The Dual Role of AI:**
> "AI played **two roles** here: (1) LLM-assisted coding accelerated development of the parsers themselves, and (2) runtime LLM inference is reserved for formats that genuinely resist deterministic parsing."

**Data Validation:**
> "We benchmarked DataCite to Dublin Core conversion: **85.7% field coverage**, **79.2% value overlap**. All rules exported as **SSSOM TSV** files - a community standard for sharing ontology mappings - in version-controlled repository."

---

### **Part 6: Technology & Impact (1 minute)**

**Technical Stack:**
- Python 3.12 + uv package manager
- **SurrealDB** knowledge graph (standards as nodes, rules as edges)
- **Blablador** (Helmholtz-AI LLM) for fallback extraction
- **SSSOM** format export (interoperability standard)
- **OAI-PMH** live repository integration

**Broader Impact:**
> "This pattern applies beyond metadata: any domain where **specification documents have resisted automation** can benefit from hybrid deterministic-LLM pipelines that turn fragmented human-readable documentation into machine-executable infrastructure."

---

## Backup Slides / Screenshots to Prepare

In case of network issues or demo failure:

1. **Graph visualization** (full view)
2. **Graph close-up** (click green edge showing deterministic extraction)
3. **Streamlit Crosswalk Browser** (showing numbered dropdown + rules table)
4. **Successful conversion** (HZI record → DataCite XML with metrics)
5. **Pipeline statistics** from TALK_RESULTS_SNAPSHOT.md

---

## Troubleshooting During Demo

**Graph doesn't load:**
- Fallback: Show screenshot
- Explain: "This is the interactive version - for time, here's the static view"

**HZI endpoint fails:**
- Use fixture mode in Streamlit (Paste manually)
- Have sample XML ready in clipboard
- Explain: "For reliability, I'll use a cached record"

**Streamlit slow:**
- Close other browser tabs
- Restart Streamlit: `Ctrl+C`, then `uv run streamlit run app/app.py`

**Forgot a stat:**
- Open TALK_RESULTS_SNAPSHOT.md in separate terminal

---

## Practice Run (15 minutes before)

1. Open all browser tabs
2. Walk through Parts 1-6 out loud
3. Click every button you'll click in the demo
4. Time yourself (should be 7-10 minutes max)
5. Take backup screenshots
6. Close unnecessary browser tabs/apps

---

## Post-Demo Q&A Prep

**Expected Questions:**

Q: "Can you handle mappings with complex transformations, not just field-to-field?"
A: "Current implementation is field-level only - value transformations are out of scope. We focus on structural alignment, not content modification. That said, the `transform` field in our mapping rules could be extended to support simple transformations (e.g., concatenation, splitting)."

Q: "How do you handle versioning of standards?"
A: "Each standard in the graph has a version identifier (e.g., DataCite 4.4). Crosswalks are version-specific. Future work: detecting semantic drift between standard versions."

Q: "What's the accuracy of LLM extraction?"
A: "Of 20 LLM attempts, 12 succeeded (60%). We saw 8 cases where LLMs returned nothing, suggesting they're most effective as selective recovery tools, not blanket parsers. The hybrid design lets deterministic methods win when they can."

Q: "Is the graph database necessary, or could you use a relational DB?"
A: "SurrealDB gives us native graph traversal for transitive path discovery (A→B→C routing). A relational DB would require recursive CTEs or application-level path finding. The graph model aligns naturally with the domain: standards as nodes, crosswalks as edges."

Q: "Can you show a transitive conversion path?"
A: "Not implemented yet in the live demo, but the graph structure supports it. Example: if we have MARC→DC and DC→DataCite crosswalks but no direct MARC→DataCite, the system can route through Dublin Core automatically."

Q: "How do you handle conflicts when multiple crosswalks exist for the same standard pair?"
A: "Currently, we select the most recent or highest-confidence crosswalk. Future work: versioned crosswalk management, confidence aggregation, or user choice."

---

## Narrative Highlight Reel

Use these **key phrases** for maximum impact:

1. **"Graph-grounded interoperability"** (your differentiator)
2. **"Hybrid deterministic-LLM pipeline"** (technical approach)
3. **"Evidence-based mappings"** (provenance story)
4. **"Deterministic-first, LLM-as-fallback"** (design principle)
5. **"51% success rate from 37 heterogeneous sources"** (real-world validation)
6. **"LLMs as selective recovery tools, not default parsers"** (key finding)
7. **"Standards as nodes, mappings as edges"** (graph model)
8. **"Machine-executable infrastructure from human-readable documentation"** (impact)

---

## Final Checklist (5 minutes before)

- [ ] Graph server running (localhost:8000)
- [ ] Streamlit running (localhost:8501)
- [ ] Browser tabs open & tested
- [ ] HZI endpoint tested (fetch + convert working)
- [ ] Backup screenshots ready
- [ ] Water nearby
- [ ] Deep breath

**You got this! 🚀**
