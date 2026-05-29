#!/usr/bin/env python3
"""Simple HTTP server to view the crosswalk graph visualization.

Uses the proven graph-visualizer (sigma.js v3) from the submodule.

Run this script and open the printed URL.
"""

import argparse
import http.server
import shutil
import socket
import subprocess
import socketserver
import sys
import webbrowser
from pathlib import Path


def first_free_port(start: int = 8080) -> int:
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("", port))
            except OSError:
                port += 1
                continue
        return port


def patch_visualizer_html(html_path: Path) -> None:
    html = html_path.read_text(encoding="utf-8")
    html = html.replace(
        "labelRenderedSizeThreshold: 10,",
        "labelRenderedSizeThreshold: 0,",
    )
    html = html.replace(
        """            if (isSelected) {
              res.forceLabel = true;
              res.label = fullLabel;
            }
""",
        """            res.forceLabel = true;
            res.label = fullLabel;

            if (isSelected) {
              res.highlighted = true;
            }
""",
    )
    html = html.replace(
        '<button id="reset" type="button">Reset view</button>',
        '<button id="reset" type="button">Reset view</button>\n'
        '      <select id="export-format" aria-label="Export format">\n'
        '        <option value="svg">SVG</option>\n'
        '        <option value="png">PNG</option>\n'
        '      </select>\n'
        '      <button id="export-graph" type="button">Export</button>',
    )
    svg_export_code = r'''
      const exportFormatEl = document.getElementById("export-format");
      const exportGraphBtn = document.getElementById("export-graph");

      function downloadSvg(filename, svgContent) {
        const blob = new Blob([svgContent], { type: "image/svg+xml" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 250);
      }

      function downloadPng(filename, dataUrl) {
        const a = document.createElement("a");
        a.href = dataUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      }

      function escapeSvgText(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;");
      }

      function timestampForFilename() {
        const now = new Date();
        return now.getFullYear()
          + String(now.getMonth() + 1).padStart(2, "0")
          + String(now.getDate()).padStart(2, "0")
          + "_"
          + String(now.getHours()).padStart(2, "0")
          + String(now.getMinutes()).padStart(2, "0")
          + String(now.getSeconds()).padStart(2, "0");
      }

      function buildGraphSvg() {
        if (!renderer || !graph) {
          alert("Graph not loaded yet");
          return null;
        }

        const width = Math.round(container.clientWidth || 1200);
        const height = Math.round(container.clientHeight || 800);
        const edgeParts = [];
        const nodeParts = [];
        const labelParts = [];

        graph.forEachEdge((edge, attrs, source, target, sourceAttrs, targetAttrs) => {
          if (attrs.hidden || sourceAttrs.hidden || targetAttrs.hidden) return;
          const sourcePoint = renderer.graphToViewport({ x: sourceAttrs.x, y: sourceAttrs.y });
          const targetPoint = renderer.graphToViewport({ x: targetAttrs.x, y: targetAttrs.y });
          const color = attrs.color || "#999999";
          const size = Math.max(1, Number(attrs.size || 1));
          edgeParts.push(`<line x1="${sourcePoint.x.toFixed(2)}" y1="${sourcePoint.y.toFixed(2)}" x2="${targetPoint.x.toFixed(2)}" y2="${targetPoint.y.toFixed(2)}" stroke="${escapeSvgText(color)}" stroke-width="${size.toFixed(2)}" stroke-linecap="round" opacity="0.72"/>`);
        });

        graph.forEachNode((node, attrs) => {
          if (attrs.hidden) return;
          const point = renderer.graphToViewport({ x: attrs.x, y: attrs.y });
          const color = attrs.color || "#4A90E2";
          const radius = Math.max(5, Number(attrs.size || 8));
          const label = String(attrs.label || node);
          const labelX = point.x + radius + 5;
          const labelY = point.y + 4;
          const labelWidth = Math.max(18, label.length * 7.4 + 10);
          const labelHeight = 18;
          nodeParts.push(`<circle cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="${radius.toFixed(2)}" fill="${escapeSvgText(color)}" stroke="#ffffff" stroke-width="1.5"/>`);
          labelParts.push(`<rect x="${(labelX - 4).toFixed(2)}" y="${(labelY - 13).toFixed(2)}" width="${labelWidth.toFixed(2)}" height="${labelHeight}" rx="3" ry="3" fill="#ffffff" opacity="0.86"/>`);
          labelParts.push(`<text x="${labelX.toFixed(2)}" y="${labelY.toFixed(2)}" font-family="Arial, Helvetica, sans-serif" font-size="13" font-weight="600" fill="#1f2933">${escapeSvgText(label)}</text>`);
        });

        return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <g id="edges">
    ${edgeParts.join("\n    ")}
  </g>
  <g id="nodes">
    ${nodeParts.join("\n    ")}
  </g>
  <g id="labels">
    ${labelParts.join("\n    ")}
  </g>
</svg>`;
      }

      function exportGraphAsSvg() {
        const svg = buildGraphSvg();
        if (!svg) return;
        const timestamp = timestampForFilename();

        downloadSvg(`m2s3om_crosswalk_graph_${timestamp}.svg`, svg);
      }

      function exportGraphAsPng() {
        const svg = buildGraphSvg();
        if (!svg) return;

        const width = Math.round(container.clientWidth || 1200);
        const height = Math.round(container.clientHeight || 800);
        const svgBlob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
        const url = URL.createObjectURL(svgBlob);
        const image = new Image();
        image.onload = () => {
          const canvas = document.createElement("canvas");
          canvas.width = width;
          canvas.height = height;
          const context = canvas.getContext("2d");
          context.fillStyle = "#ffffff";
          context.fillRect(0, 0, width, height);
          context.drawImage(image, 0, 0, width, height);
          URL.revokeObjectURL(url);
          downloadPng(
            `m2s3om_crosswalk_graph_${timestampForFilename()}.png`,
            canvas.toDataURL("image/png"),
          );
        };
        image.onerror = () => {
          URL.revokeObjectURL(url);
          alert("PNG export failed. Try Export SVG instead.");
        };
        image.src = url;
      }

      exportGraphBtn?.addEventListener("click", () => {
        if (exportFormatEl?.value === "png") {
          exportGraphAsPng();
        } else {
          exportGraphAsSvg();
        }
      });
'''
    html = html.replace(
        "      function downloadJson(filename, obj) {",
        f"{svg_export_code}\n      function downloadJson(filename, obj) {{",
    )
    html_path.write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Serve the M2S3OM graph visualizer")
    parser.add_argument("--open", action="store_true", help="Open the browser automatically")
    parser.add_argument(
        "--renderer",
        choices=["sigma", "cytoscape", "both"],
        default="sigma",
        help="Which renderer to open: sigma (default), cytoscape, or both",
    )
    args = parser.parse_args()

    port = first_free_port(8080)
    root = Path(__file__).resolve().parents[1]
    source_web_dir = root / "graph-visualizer" / "web"
    web_dir = root / "exports" / "graph_visualizer_web"
    human_graph = root / "data" / "crosswalks.human.json"
    graphology_graph = web_dir / "graphs" / "automatic_hm_graph.graphology.json"

    if web_dir.exists():
        shutil.rmtree(web_dir)
    shutil.copytree(source_web_dir, web_dir)
    patch_visualizer_html(web_dir / "sigma_sources_services_graph.html")

    subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "convert_to_human_graph.py"),
            "--output",
            str(human_graph),
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(root / "graph-visualizer" / "scripts" / "human_to_graphology.py"),
            "--input",
            str(human_graph),
            "--output",
            str(graphology_graph),
        ],
        check=True,
    )

    sigma_url = f"http://localhost:{port}/sigma_sources_services_graph.html"
    cytoscape_url = f"http://localhost:{port}/cytoscape_graph.html"

    print(f"Starting HTTP server on port {port}...")
    print(f"Serving files from: {web_dir}")
    print(f"\nSigma.js renderer:     {sigma_url}")
    print(f"Cytoscape.js renderer: {cytoscape_url}")
    print("\nPress Ctrl+C to stop the server")

    # Select which URL(s) to open
    if args.renderer == "sigma":
        open_urls = [sigma_url]
    elif args.renderer == "cytoscape":
        open_urls = [cytoscape_url]
    else:  # "both"
        open_urls = [sigma_url, cytoscape_url]

    import os
    os.chdir(web_dir)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        if args.open:
            for url in open_urls:
                webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")


if __name__ == "__main__":
    main()
