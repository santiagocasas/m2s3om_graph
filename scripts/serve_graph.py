#!/usr/bin/env python3
"""Simple HTTP server to view the crosswalk graph visualization.

Uses the proven graph-visualizer (sigma.js v3) from the submodule.

Run this script and open the printed URL.
"""

import argparse
import http.server
import socket
import subprocess
import socketserver
import sys
import shutil
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


def main():
    parser = argparse.ArgumentParser(description="Serve the M2S3OM graph visualizer")
    parser.add_argument("--open", action="store_true", help="Open the browser automatically")
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

    url = f"http://localhost:{port}/sigma_sources_services_graph.html"

    print(f"Starting HTTP server on port {port}...")
    print(f"Serving files from: {web_dir}")
    print(f"\nOpen in browser: {url}")
    print("Press Ctrl+C to stop the server")

    import os
    os.chdir(web_dir)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        if args.open:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")


if __name__ == "__main__":
    main()
