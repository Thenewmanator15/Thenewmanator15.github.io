"""Build a throwaway copy of the site with extra pages, for tests that need the real templates."""
import contextlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ZOLA_DEFAULT = Path("G:/dev/tools/zola-v0.23.6/zola.exe")


def zola() -> str:
    return os.environ.get("ZOLA") or shutil.which("zola") or str(ZOLA_DEFAULT)


@contextlib.contextmanager
def built_site(extra: dict[str, str]):
    """Copy config, templates, static, data and content to a temp dir, add each `extra` file
    (path relative to content/), build with Zola and yield the output folder."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        shutil.copy2(ROOT / "config.toml", root / "config.toml")
        for name in ("templates", "static", "data", "content"):
            shutil.copytree(ROOT / name, root / name)
        for rel, text in extra.items():
            path = root / "content" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        run = subprocess.run([zola(), "--root", str(root), "build", "--output-dir", str(root / "public")],
                             capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(f"zola build failed:\n{run.stdout}\n{run.stderr}")
        yield root / "public"
