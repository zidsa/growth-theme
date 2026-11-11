"""Serve a theme's assets/ dir the way Vitrin's asset_url addresses them.

asset_url renders <domain>/<theme hash>/<path>?v=..., so the first path segment
is dropped and the rest is served from the assets root.
Usage: python3 -I asset_server.py <port> <assets dir>
"""

import functools
import http.server
import sys


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split("?", 1)[0]
        parts = path.lstrip("/").split("/", 1)
        return super().translate_path("/" + (parts[1] if len(parts) == 2 else ""))

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


port, root = int(sys.argv[1]), sys.argv[2]
http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=root)).serve_forever()
