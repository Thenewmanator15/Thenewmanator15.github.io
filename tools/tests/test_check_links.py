import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_links import check, collect  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class Collect(unittest.TestCase):
    def test_collects_every_public_link_once(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root / "content" / "ch" / "p" / "index.md",
                  '+++\ntitle = "P"\n[extra]\n[[extra.proof]]\nkind = "code"\nlabel = "Code"\n'
                  'url = "https://github.com/x/y"\narchive = "https://doi.org/10.5281/zenodo.1"\n'
                  '[[extra.proof]]\nkind = "photos"\nlabel = "Photos"\nurl = "#photos"\n'
                  '[[extra.proof]]\nkind = "document"\nlabel = "Report"\nurl = "report.pdf"\n+++\nBody.\n')
            write(root / "content" / "ch" / "q.md",
                  '+++\ntitle = "Q"\n[extra]\n[[extra.proof]]\nkind = "code"\nlabel = "Code"\nurl = "https://github.com/x/y"\n+++\n')
            write(root / "data" / "site.toml",
                  '[[links]]\nlabel = "GitHub"\nurl = "https://github.com/x"\n[[links]]\nlabel = "How"\nurl = "/how/"\n'
                  '[[profiles]]\nname = "ORCID"\nurl = "https://orcid.org/0000-0000-0000-0001"\nhandle = "x"\nline = "Research"\n'
                  '[try_it]\nname = "Try"\nurl = "https://demo.example/"\nline = "A demo"\n')
            write(root / "data" / "timeline.toml",
                  '[[entries]]\nid = "a"\n[[entries.proof]]\nkind = "certificate"\nlabel = "C"\nurl = "https://cert.example/1"\n')
            got = sorted(collect(root / "content", root / "data"))
            self.assertEqual(got, ["https://cert.example/1", "https://demo.example/", "https://doi.org/10.5281/zenodo.1",
                                   "https://github.com/x", "https://github.com/x/y",
                                   "https://orcid.org/0000-0000-0000-0001"])


class Check(unittest.TestCase):
    def test_reports_dead_links_and_retries_flaky_ones(self):
        calls = {}

        def fetch(url):
            calls[url] = calls.get(url, 0) + 1
            if url.endswith("/flaky") and calls[url] == 1:
                raise OSError("timed out")
            return 404 if url.endswith("/gone") else 200

        out = check(["https://a.example/ok", "https://a.example/gone", "https://a.example/flaky",
                     "https://www.linkedin.com/in/someone"], fetch=fetch, pause=0)
        self.assertEqual(len(out), 1)
        self.assertIn("https://a.example/gone", out[0])
        self.assertNotIn("https://www.linkedin.com/in/someone", calls)  # LinkedIn refuses robots: skipped
        self.assertEqual(calls["https://a.example/flaky"], 2)


class Serve(unittest.TestCase):
    def test_modules_are_served_as_javascript(self):
        import threading
        import urllib.request

        from serve_static import make_server
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.mjs").write_text("export const x = 1;\n", encoding="utf-8")
            server = make_server(d, 0)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                port = server.server_address[1]
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/a.mjs", timeout=5) as r:
                    self.assertTrue(r.headers["Content-Type"].startswith("text/javascript"))
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
