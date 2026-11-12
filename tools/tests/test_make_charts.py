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

    def test_coordinates_are_rounded_but_text_is_not(self):
        # matplotlib writes six decimals; two are invisible on screen and keep pages small
        svg = SAMPLE.replace('d="M0 0"', 'd="M 12.345678 -9.876543 L 1e-05 3"').replace(
            ">1.0</text>", ' x="1.23456" transform="translate(3.14159 2.71828)">0.023%</text>')
        out = themed(svg)
        self.assertIn('d="M 12.35 -9.88 L 1e-05 3"', out)
        self.assertIn('x="1.23"', out)
        self.assertIn('transform="translate(3.14 2.72)"', out)
        self.assertIn(">0.023%</text>", out)

    def test_unused_ids_comments_and_indents_dropped(self):
        svg = SAMPLE.replace('<path d="M0 0"', '\n   <!-- a note -->\n   <g id="figure_1"><path id="m1" d="M0 0"').replace(
            "</svg>", '</g><use xlink:href="#m1"/></svg>')
        out = themed(svg, "pdn")
        self.assertNotIn('id="pdn-figure_1"', out)
        self.assertIn('id="pdn-m1"', out)
        self.assertNotIn("a note", out)
        self.assertNotIn("\n   ", out)

    def test_grid_and_trace_placeholders(self):
        self.assertIn('class="s-grid"', themed(SAMPLE.replace("#000003", "#000007")))
        self.assertIn('class="s-trace"', themed(SAMPLE.replace("#000003", "#000008")))

    def test_every_chart_csv_names_its_source(self):
        figs = ROOT / "data" / "figures"
        names = ("link", "sweep", "timing", "ble-error", "carrier", "fuzz")
        for name in names:
            self.assertTrue((figs / f"sniffer-{name}.csv").exists(), name)
            self.assertTrue((figs / f"sniffer-{name}.svg").exists(), name)
        for csv in figs.glob("sniffer-*.csv"):
            first = csv.read_text(encoding="utf-8").splitlines()[0]
            self.assertTrue(first.startswith("# source:"), csv.name)

    def test_sniffer_tiles_agree_with_the_fuzz_data(self):
        import csv
        with open(ROOT / "data" / "figures" / "sniffer-fuzz.csv", encoding="utf-8", newline="") as f:
            total = sum(int(r["inputs"]) for r in csv.DictReader(l for l in f if not l.startswith("#")))
        page = (ROOT / "content" / "rf-wireless-embedded" / "sniffers" / "index.md").read_text(encoding="utf-8")
        self.assertIn(f'value = "{total:,}"', page)
        self.assertIn(f"That is {total:,} in all.", page)

    def test_carrier_chart_names_the_board_that_measured(self):
        text = (ROOT / "data" / "figures" / "sniffer-carrier.csv").read_text(encoding="utf-8")
        self.assertIn("measured by the ESP32-C6", text)
        page = (ROOT / "content" / "rf-wireless-embedded" / "sniffers" / "index.md").read_text(encoding="utf-8")
        self.assertNotIn("reading on the nRF54L15", page)

    def test_driver_rejection_matches_the_thesis(self):
        # poly6 rows of the thesis width sweep; ends match bng-driver.json cmrr-slowest and cmrr-fastest
        import csv
        path = ROOT / "data" / "figures" / "driver-rejection.csv"
        self.assertTrue(path.read_text(encoding="utf-8").startswith("# source:"))
        with open(path, encoding="utf-8", newline="") as f:
            data = list(csv.DictReader(l for l in f if not l.startswith("#")))
        self.assertEqual(len(data), 15)
        by_rate = sorted(data, key=lambda r: float(r["rate_mhz"]))
        self.assertAlmostEqual(float(by_rate[0]["rate_mhz"]), 5.01, places=2)
        self.assertAlmostEqual(float(by_rate[0]["cmrr_db"]), 38.53, places=2)
        self.assertAlmostEqual(float(by_rate[-1]["rate_mhz"]), 53.48, places=2)
        self.assertAlmostEqual(float(by_rate[-1]["cmrr_db"]), 20.16, places=2)
        self.assertTrue((ROOT / "data" / "figures" / "driver-rejection.svg").exists())

    def test_phd_mass_reach_matches_the_thesis(self):
        # thesis assets/values/mass-reach.json: 43.19 us and 0.2315 % at m/z 100, 0.02315 % at m/z 10,000
        import csv
        path = ROOT / "data" / "figures" / "phd-mass-reach.csv"
        self.assertTrue(path.read_text(encoding="utf-8").startswith("# source:"))
        with open(path, encoding="utf-8", newline="") as f:
            data = {float(r["mz"]): r for r in csv.DictReader(l for l in f if not l.startswith("#"))}
        self.assertAlmostEqual(float(data[100]["flight_us"]), 43.19, places=2)
        self.assertAlmostEqual(float(data[100]["pulsed_pct"]), 0.2315, places=4)
        self.assertAlmostEqual(float(data[10000]["pulsed_pct"]), 0.02315, places=5)
        self.assertTrue(all(float(r["coded_pct"]) == 50 for r in data.values()))
        self.assertTrue((ROOT / "data" / "figures" / "phd-mass-reach.svg").exists())

    def test_hand_drawn_sniffer_diagrams_exist(self):
        for name in ("datapath", "header", "retune"):
            svg = (ROOT / "data" / "figures" / f"sniffer-{name}.svg").read_text(encoding="utf-8")
            self.assertTrue(svg.startswith('<svg class="chart" aria-hidden="true" focusable="false"'), name)
            for i in re.findall(r'id="([^"]+)"', svg):
                self.assertTrue(i.startswith(f"sniffer-{name}-"), i)

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
