"""Serves a built copy of the site on 127.0.0.1 for the accessibility check, so pa11y tests the
same files that get deployed (zola serve adds a live-reload script). JavaScript modules are sent
as text/javascript, which browsers require.

Usage: python tools/serve_static.py <folder> <port>
"""
from __future__ import annotations

import functools
import http.server
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".mjs": "text/javascript", ".js": "text/javascript"}

    def log_message(self, *args):  # quiet: the check's own output is what matters
        pass


def make_server(directory: str, port: int) -> http.server.ThreadingHTTPServer:
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=directory))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: serve_static.py FOLDER PORT", file=sys.stderr)
        return 2
    make_server(argv[0], int(argv[1])).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
