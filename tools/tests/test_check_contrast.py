import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_contrast import _pairs, check, contrast, opacity_problems  # noqa: E402

BACKGROUNDS = ["page", "bezel", "panel", "screen", "btn", "zbg", "tagbg", "grid"]
FOREGROUNDS = ["pagetext", "paneldim", "text", "dim", "btntext", "btnedge", "trace",
               "ztext", "zdim", "dig", "cm"]


def theme(**over: str) -> str:
    """One complete, passing theme block body: white text on black, yellow accents and channels."""
    t = {k: "#000000" for k in BACKGROUNDS} | {k: "#ffffff" for k in FOREGROUNDS}
    t |= {f"c{n}": "#ffff00" for n in range(1, 8)}
    t |= {"accent": "#ffff00", "onaccent": "#000000", "chtext": "#000000", "glow": "none"}
    t |= {k.replace("_", "-"): v for k, v in over.items()}
    return ";".join(f"--{k}:{v}" for k, v in t.items())


def sheet(scope=None, paper=None, hc=None, light=None, more=None, forced=True) -> str:
    scope, paper, hc = scope or theme(), paper or theme(), hc or theme()
    css = (f":root{{--sans:system-ui}}\n:root,html[data-style=scope]{{{scope}}}\n"
           f"html[data-style=paper]{{{paper}}}\nhtml[data-style=hc]{{{hc}}}\n"
           f"@media (prefers-color-scheme: light){{html:not([data-style]){{{light or paper}}}}}\n"
           f"@media (prefers-contrast: more){{html:not([data-style]){{{more or hc}}}}}\n")
    if forced:
        css += "@media (forced-colors: active){html:not([data-style]),html[data-style]{--page:Canvas}}\n"
    return css


class Contrast(unittest.TestCase):
    def test_chart_text_on_screen_is_checked(self):
        pairs = _pairs({"c1": "#ffff00"})
        self.assertIn(("pagetext", "screen"), pairs)
        self.assertIn(("paneldim", "screen"), pairs)

    def test_panel_header_and_cards_are_checked(self):
        pairs = _pairs({"c1": "#ffff00"})
        for pair in (("pagetext", "panel"), ("paneldim", "panel")):
            self.assertIn(pair, pairs)

    def test_contrast_known_pair(self):
        self.assertEqual(round(contrast("#000000", "#ffffff"), 1), 21.0)

    def test_contrast_is_symmetric_and_reads_short_hex(self):
        self.assertAlmostEqual(contrast("#fff", "#777777"), contrast("#777777", "#ffffff"))
        self.assertEqual(round(contrast("#777", "#fff"), 2), 4.48)


class Check(unittest.TestCase):
    def test_every_theme_passes(self):
        css = (ROOT / "static" / "css" / "tokens.css").read_text(encoding="utf-8")
        self.assertEqual(check(css), [])

    def test_good_sheet_passes(self):
        self.assertEqual(check(sheet()), [])

    def test_low_contrast_pair_named_with_its_theme(self):
        out = check(sheet(paper=theme(dim="#222222")))
        # --dim is checked on --screen, --grid and --zbg; the light-scheme copy matches paper, so no repeats
        self.assertEqual(len(out), 3)
        self.assertTrue(all(p.startswith("paper: --dim") for p in out), out)
        self.assertTrue(any("paper" in p and "--dim" in p and "--screen" in p for p in out))

    def test_in_progress_label_checked_on_the_page(self):
        # the "in progress" label is accent-coloured text on the page background
        out = check(sheet(paper=theme(accent="#111111")))
        self.assertTrue(any("--accent" in p and "--page" in p for p in out), out)

    def test_channel_button_text_checked_on_each_channel(self):
        out = check(sheet(hc=theme(c4="#333333")))
        self.assertTrue(any("--chtext" in p and "--c4" in p for p in out))

    def test_missing_token_reported(self):
        out = check(sheet(scope=theme().replace(";--tagbg:#000000", "")))
        self.assertTrue(any("scope" in p and "--tagbg" in p for p in out))

    def test_channels_must_match_across_themes(self):
        out = check(sheet(paper=theme(c8="#ffff00")))
        self.assertTrue(any("--c8" in p for p in out))

    def test_media_fallback_must_match_its_theme(self):
        out = check(sheet(light=theme(text="#eeeeee")))
        self.assertTrue(any("prefers-color-scheme" in p and "--text" in p for p in out))

    def test_forced_colors_block_required(self):
        self.assertTrue(any("forced-colors" in p for p in check(sheet(forced=False))))

    def test_pairs_found_in_review(self):
        # key-figure labels on --grid, page text in --paneldim, pressed digital buttons, text in the zoom pane
        for bad, pair in [({"grid": "#eeeeee"}, ("--dim", "--grid")), ({"page": "#ffffff"}, ("--paneldim", "--page")),
                          ({"dig": "#000000"}, ("--chtext", "--dig")), ({"zbg": "#ffffff"}, ("--text", "--zbg"))]:
            out = check(sheet(scope=theme(**bad)))
            self.assertTrue(any(pair[0] in p and pair[1] in p for p in out), (bad, out))

    def test_no_text_is_faded_with_opacity(self):
        self.assertEqual(opacity_problems(".ov.dim{opacity:.4}\n#toast{opacity:0}\n#toast.on{opacity:1}"), [])
        self.assertEqual(opacity_problems(".chb.quiet { opacity: .55; }"), [".chb.quiet"])
        for name in ("scope.css", "pages.css"):
            css = (ROOT / "static" / "css" / name).read_text(encoding="utf-8")
            self.assertEqual(opacity_problems(css), [], name)

    def test_non_hex_colour_in_a_pair_reported(self):
        out = check(sheet(scope=theme(text="rgb(255,255,255)")))
        self.assertTrue(any("--text" in p and "hex" in p for p in out))


if __name__ == "__main__":
    unittest.main()
