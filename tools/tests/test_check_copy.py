import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from check_copy import check_paths, problems  # noqa: E402


class Ands(unittest.TestCase):
    def test_two_ands_in_a_sentence(self):
        self.assertNotEqual(problems("I built it and tested it and shipped it."), [])

    def test_one_and_is_fine(self):
        self.assertEqual(problems("I built it and tested it."), [])

    def test_names_with_and_allowed(self):
        self.assertEqual(problems("I taught High-Speed and Mixed-Signal Design."), [])
        self.assertEqual(problems("I read Howard Johnson and Eric Bogatin, then built it and tested it."), [])

    def test_channel_names_allowed(self):
        names = ["RF, wireless and embedded", "Measurement data and signal processing"]
        self.assertEqual(problems("Work in RF, wireless and embedded, built and tested.", allowed=names), [])

    def test_comma_before_and(self):
        self.assertNotEqual(problems("Bluetooth, and Wi-Fi."), [])


class Punctuation(unittest.TestCase):
    def test_em_dash_and_curly_quotes(self):
        self.assertNotEqual(problems("It works — mostly."), [])
        self.assertNotEqual(problems("It’s here."), [])

    def test_en_dash_in_ranges_allowed(self):
        self.assertEqual(problems("2017 – 2024"), [])


class Words(unittest.TestCase):
    def test_banned_words(self):
        for w in ["delve", "robust", "seamless", "leverage", "pivotal", "showcase", "meticulous",
                  "additionally", "crucial", "enhance", "foster", "garner", "highlights",
                  "landscape", "tapestry", "testament", "underscore", "vibrant"]:
            self.assertNotEqual(problems(f"A {w} design."), [], w)

    def test_code_highlighting_allowed(self):
        self.assertEqual(problems("Code highlighting still works."), [])

    def test_phd_awarded_claims(self):
        self.assertNotEqual(problems("Dr Mathew Newman"), [])
        self.assertNotEqual(problems("I hold a PhD in electronics."), [])
        self.assertEqual(problems("PhD candidate, thesis not submitted."), [])


class Skipping(unittest.TestCase):
    def test_code_and_urls_skipped(self):
        self.assertEqual(problems("Run `a and b and c` from https://x.example/and-and-and."), [])


class Files(unittest.TestCase):
    def test_markdown_front_matter_and_body(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content" / "p"
            c.mkdir(parents=True)
            (c / "index.md").write_text(
                '+++\ntitle = "A robust thing"\n[extra]\nmy_part = "I built it."\n+++\n'
                "Body text and more and more.\n", encoding="utf-8")
            out = check_paths([Path(d) / "content"])
            self.assertEqual(len(out), 2)

    def test_template_and_js_text(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "templates"
            t.mkdir()
            (t / "a.html").write_text('<p>{{ x }} Seamless view</p><button aria-label="Zoom in">+</button>', encoding="utf-8")
            j = Path(d) / "js"
            j.mkdir()
            (j / "a.mjs").write_text('const s = "It works — mostly";\nconst id = "ch-1";\n', encoding="utf-8")
            out = check_paths([t, j])
            self.assertEqual(len(out), 2)

    def test_channel_names_read_from_the_channels_file(self):
        with tempfile.TemporaryDirectory() as d:
            data = Path(d) / "data"
            data.mkdir()
            (data / "channels.toml").write_text('[[channels]]\nn = 2\nname = "RF, wireless and embedded"\nslug = "rf"\n'
                                                'colour = "--c2"\narchived = false\n', encoding="utf-8")
            content = Path(d) / "content"
            content.mkdir()
            (content / "a.md").write_text('+++\ntitle = "A"\n+++\nWork in RF, wireless and embedded, built and tested.\n',
                                          encoding="utf-8")
            self.assertEqual(check_paths([content, data]), [])

    def test_figure_component_alt_and_caption_checked(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content"
            c.mkdir()
            (c / "a.md").write_text('+++\ntitle = "A"\n+++\n{{ <figure src="x.jpg" alt="A robust board" '
                                    'caption="Built and tested and shipped." /> }}\n', encoding="utf-8")
            out = check_paths([c])
            self.assertTrue(any("robust" in p for p in out), out)
            self.assertTrue(any("two 'and's" in p for p in out), out)

    def test_chart_component_alt_and_caption_checked(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content"
            c.mkdir()
            (c / "a.md").write_text('+++\ntitle = "A"\n+++\n{{ <chart name="x" alt="A robust plot" '
                                    'caption="Fast, and small." /> }}\n', encoding="utf-8")
            out = check_paths([c])
            self.assertTrue(any("robust" in p for p in out), out)
            self.assertTrue(any("comma before" in p for p in out), out)

    def test_matrix_and_tiles_checked(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content"
            c.mkdir()
            (c / "a.md").write_text(
                '+++\ntitle = "A"\n[extra]\npanel = true\n[[extra.matrix]]\ntitle = "A seamless radio"\n'
                'cols = ["A"]\nrows = [["Capture, and survey", "yes"]]\nnotes = ["It is crucial."]\n'
                '[[extra.tiles]]\nvalue = "8"\nlabel = "vibrant vectors"\n+++\n', encoding="utf-8")
            out = " | ".join(check_paths([c]))
            for word in ("seamless", "crucial", "vibrant", "comma before"):
                self.assertIn(word, out)

    def test_html_tags_skipped_but_their_text_checked(self):
        # A fold's heading id ("how-i-learned-it-and-checked-it") isn't prose; its title and text are.
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content"
            c.mkdir()
            (c / "a.md").write_text(
                '+++\ntitle = "A"\n+++\n<details class="fold"><summary><h2 id="tested-and-checked-and-signed">'
                'Tested and checked.</h2></summary>\n\nIt worked.\n\n</details>\n\n'
                '<details class="fold"><summary><h2 id="b">Fast, and small.</h2></summary>\n\nOk.\n\n</details>\n',
                encoding="utf-8")
            out = check_paths([c])
            self.assertFalse(any("two 'and's" in p for p in out), out)
            self.assertTrue(any("comma before" in p for p in out), out)

    def test_table_cells_are_checked_one_at_a_time(self):
        # cells have no full stops, so a table must not read as one long sentence
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content"
            c.mkdir()
            (c / "a.md").write_text(
                '+++\ntitle = "A"\n+++\n| Where | What |\n|---|---|\n| Chips | before and after |\n'
                '| Cells | in and out |\n| Paint | fast, and small |\n', encoding="utf-8")
            out = check_paths([c])
            self.assertFalse(any("two 'and's" in p for p in out), out)
            self.assertTrue(any("comma before" in p for p in out), out)

    def test_missing_folder_skipped(self):
        self.assertEqual(check_paths([Path("does-not-exist")]), [])

    def test_wip_note_checked(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content" / "p"
            c.mkdir(parents=True)
            (c / "index.md").write_text(
                '+++\ntitle = "A page"\n[extra]\nstill_to_come = ["photos"]\n'
                'still_to_come_note = "Photos are a robust thing to wait for."\n+++\n', encoding="utf-8")
            out = check_paths([Path(d) / "content"])
            self.assertTrue(any("robust" in p for p in out), out)


if __name__ == "__main__":
    unittest.main()
