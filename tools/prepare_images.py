"""Make web copies of photos for a project page.

Usage: python tools/prepare_images.py "<OneDrive>/Portfolio originals/<topic>/<project>" content/<topic>/<project>

The originals stay in the private OneDrive folder and are never changed. Each copy is turned the
right way up, shrunk so its long edge is at most 2400 px, and saved with no EXIF or XMP (so no
GPS position or phone model reaches the public site). HEIC and JPEG become JPEG at quality 85,
stepping down to 70 if a copy is still over 2 MB. PNG stays PNG (screenshots, transparency).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

PHOTO_EXT = {".jpg", ".jpeg", ".heic", ".heif"}
PNG_EXT = {".png"}
QUALITIES = (85, 80, 75, 70)
MAX_BYTES = 2 * 1024 * 1024


def _encode(im: Image.Image, fmt: str, quality: int, icc: bytes | None) -> bytes:
    buf = io.BytesIO()
    kwargs = {"icc_profile": icc} if icc else {}
    if fmt == "JPEG":
        im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True, exif=b"", **kwargs)
    else:
        im.save(buf, "PNG", optimize=True, **kwargs)
    return buf.getvalue()


def prepare(src: Path, dest_dir: Path, max_edge: int = 2400, max_bytes: int = MAX_BYTES) -> Path:
    src, dest_dir = Path(src), Path(dest_dir)
    if dest_dir.resolve() == src.parent.resolve():
        raise ValueError(f"refusing to write into the originals folder: {dest_dir}")
    is_png = src.suffix.lower() in PNG_EXT
    fmt = "PNG" if is_png else "JPEG"
    out = dest_dir / (src.stem + (".png" if is_png else ".jpg"))

    with Image.open(src) as opened:
        icc = opened.info.get("icc_profile")
        im = ImageOps.exif_transpose(opened)
    im.info = {}  # drop EXIF, XMP and comments; the colour profile is passed back in on save
    im.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    if fmt == "JPEG" and im.mode != "RGB":
        im = im.convert("RGB")

    data = b""
    for q in QUALITIES:
        data = _encode(im, fmt, q, icc)
        if len(data) <= max_bytes or fmt == "PNG":
            break
    dest_dir.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    if len(data) > max_bytes:
        print(f"warning: {out.name} is {len(data) / 1024 / 1024:.1f} MB even at the lowest quality",
              file=sys.stderr)
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: prepare_images.py ORIGINALS_FOLDER PROJECT_FOLDER", file=sys.stderr)
        return 2
    src_dir, dest_dir = Path(argv[0]), Path(argv[1])
    for f in sorted(src_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in PHOTO_EXT | PNG_EXT:
            print(prepare(f, dest_dir).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
