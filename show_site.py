#!/usr/bin/env python3
"""Start a local HTTP server and open index.html in the browser."""

import http.server
import os
import threading
import webbrowser
from pathlib import Path

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"

PORT = 8765
ROOT = Path(__file__).parent.resolve()
URL  = f"http://localhost:{PORT}/"


def main() -> None:
    os.chdir(ROOT)

    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *_: None  # suppress request logs

    server = http.server.HTTPServer(("", PORT), handler)

    print(f"\n  {BOLD}Live server{RESET}  {DIM}serving {ROOT}{RESET}")
    print(f"  {CYAN}{URL}{RESET}")
    print(f"  {DIM}Ctrl-C to stop{RESET}\n")

    threading.Timer(0.1, lambda: webbrowser.open(URL)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  {DIM}Server stopped.{RESET}\n")


if __name__ == "__main__":
    main()
