import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import ExifTags, Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from prepare_images import main, prepare  # noqa: E402


def make_jpeg(path: Path, size, exif=None, xmp=None, noise=False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.effect_noise(size, 80).convert("RGB") if noise else Image.new("RGB", size, (200, 80, 40))
    kwargs = {"quality": 95}
    if exif is not None:
        kwargs["exif"] = exif
    if xmp is not None:
        kwargs["xmp"] = xmp
    im.save(path, "JPEG", **kwargs)
    return path


def make_jpeg_with_gps(path: Path) -> Path:
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "TestPhone"
    exif[ExifTags.IFD.GPSInfo] = {1: "N", 2: (51.0, 30.0, 0.0), 3: "W", 4: (2.0, 35.0, 0.0)}
    xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><exif:GPSLatitude>51,30N</exif:GPSLatitude></x:xmpmeta>'
    return make_jpeg(path, (640, 480), exif=exif, xmp=xmp)


def make_heic(path: Path) -> Path:
    import pillow_heif
    pillow_heif.register_heif_opener()
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 480), (10, 120, 200)).save(path, format="HEIF")
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Prepare(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.src = tmp / "originals"
        self.dest = tmp / "repo"

    def tearDown(self):
        self._tmp.cleanup()

    def test_resizes_long_edge(self):
        out = prepare(make_jpeg(self.src / "big.jpg", (5000, 3000)), self.dest)
        with Image.open(out) as im:
            self.assertEqual(max(im.size), 2400)
        self.assertEqual(out.parent, self.dest)

    def test_small_image_not_upscaled(self):
        out = prepare(make_jpeg(self.src / "s.jpg", (800, 600)), self.dest)
        with Image.open(out) as im:
            self.assertEqual(im.size, (800, 600))

    def test_gps_exif_and_xmp_removed(self):
        out = prepare(make_jpeg_with_gps(self.src / "g.jpg"), self.dest)
        with Image.open(out) as im:
            self.assertFalse(im.getexif())
        self.assertNotIn(b"GPS", out.read_bytes())
        self.assertNotIn(b"TestPhone", out.read_bytes())

    def test_orientation_applied_before_exif_dropped(self):
        exif = Image.Exif()
        exif[ExifTags.Base.Orientation] = 6  # camera held sideways: rotate 90 degrees
        out = prepare(make_jpeg(self.src / "r.jpg", (400, 200), exif=exif), self.dest)
        with Image.open(out) as im:
            self.assertEqual(im.size, (200, 400))
            self.assertFalse(im.getexif())

    def test_heic_becomes_jpg_and_original_stays(self):
        src = make_heic(self.src / "m.heic")
        before = digest(src)
        out = prepare(src, self.dest)
        self.assertEqual(out.suffix, ".jpg")
        self.assertEqual(digest(src), before)
        with Image.open(out) as im:
            self.assertEqual(im.format, "JPEG")

    def test_quality_steps_down_to_fit(self):
        src = make_jpeg(self.src / "n.jpg", (1200, 1200), noise=True)
        loose = prepare(src, self.dest / "a").stat().st_size
        tight = prepare(src, self.dest / "b", max_bytes=loose - 1).stat().st_size
        self.assertLess(tight, loose)

    def test_refuses_to_write_into_the_originals_folder(self):
        src = make_jpeg(self.src / "same.jpg", (100, 100))
        before = digest(src)
        with self.assertRaises(ValueError):
            prepare(src, self.src)
        self.assertEqual(digest(src), before)


class Command(unittest.TestCase):
    def test_folder_to_folder_skips_other_files(self):
        with tempfile.TemporaryDirectory() as d:
            src, dest = Path(d) / "originals", Path(d) / "repo"
            make_jpeg(src / "a.jpg", (300, 200))
            make_heic(src / "b.heic")
            (src / "notes.txt").write_text("not an image", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                self.assertEqual(main([str(src), str(dest)]), 0)
            self.assertEqual(len(printed.getvalue().splitlines()), 2)
            self.assertEqual(sorted(p.name for p in dest.iterdir()), ["a.jpg", "b.jpg"])


if __name__ == "__main__":
    unittest.main()
