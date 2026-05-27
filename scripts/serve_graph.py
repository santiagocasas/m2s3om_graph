#!/usr/bin/env python3
"""Simple HTTP server to view the graph visualization.

Run this script and open http://localhost:8000 in your browser.
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path


def main():
    port = 8000
    graph_dir = Path(__file__).resolve().parents[1] / "exports" / "graph"
    
    print(f"Starting HTTP server on port {port}...")
    print(f"Serving files from: {graph_dir}")
    print(f"\nOpen in browser: http://localhost:{port}")
    print("\nPress Ctrl+C to stop the server")
    
    # Change to graph directory
    import os
    os.chdir(graph_dir)
    
    # Start server
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        # Open browser automatically
        webbrowser.open(f"http://localhost:{port}")
        
        # Serve forever
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")


if __name__ == "__main__":
    main()
