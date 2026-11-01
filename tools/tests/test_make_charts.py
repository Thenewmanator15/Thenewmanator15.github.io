import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from make_charts import themed  # noqa: E402

SAMPLE = ('<?xml version="1.0"?>\n<svg width="10pt" height="10pt" viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg">'
          '<style type="text/css">*{stroke-linecap: butt}</style>'
          '<path d="M0 0" style="fill: none; stroke: #000003; stroke-width: 0.9"/>'
          '<text style="font: 10px \'DejaVu Serif\'; text-anchor: middle; fill: #000001">1.0</text></svg>')


class Themed(unittest.TestCase):
    def test_colours_become_theme_classes(self):
        out = themed(SAMPLE)
        self.assertNotIn("style", out)
        self.assertIn('class="s-c5"', out)
        self.assertIn('fill="none"', out)
        self.assertIn('class="f-fg"', out)
        self.assertIn('font-size="10"', out)
        self.assertTrue(out.startswith('<svg class="chart" aria-hidden="true"'))
        self.assertNotIn('width="10pt"', out)

    def test_a_colour_without_a_theme_stops_the_build(self):
        with self.assertRaises(ValueError):
            themed(SAMPLE.replace("#000003", "#1f77b4"))

    def test_see_through_marks_are_refused(self):
        with self.assertRaises(ValueError):
            themed(SAMPLE.replace("stroke-width: 0.9", "stroke-width: 0.9; opacity: 0.5"))

    def test_ids_carry_the_chart_name(self):
        out = themed(SAMPLE.replace('<path d="M0 0"', '<path id="m1" d="M0 0"') + '<use xlink:href="#m1" clip-path="url(#m1)"/>', "pdn")
        self.assertIn('id="pdn-m1"', out)
        self.assertIn('xlink:href="#pdn-m1"', out)
        self.assertIn('url(#pdn-m1)', out)

    def test_charts_never_share_an_id(self):
        ids = [i for svg in (ROOT / "data" / "figures").glob("*.svg")
               for i in re.findall(r'id="([^"]+)"', svg.read_text(encoding="utf-8"))]
        self.assertEqual(len(ids), len(set(ids)))

    def test_committed_charts_are_themed(self):
        for svg in (ROOT / "data" / "figures").glob("*.svg"):
            text = svg.read_text(encoding="utf-8")
            self.assertNotIn("style", text, svg.name)
            colours = set(re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{3,6})"', text))
            self.assertEqual(colours, set(), svg.name)


if __name__ == "__main__":
    unittest.main()
