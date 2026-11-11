"""Draws the site's charts from data/figures/*.csv as SVG that follows the site's themes.

The charts use the SciencePlots style, like the thesis figures. Every colour is drawn as a
placeholder and then swapped for a class (f-fg, s-c5 and so on) that pages.css maps to a
theme token, so a chart changes with the scope, paper and high-contrast themes. No style
attributes or <style> blocks are left, because the site's CSP blocks inline styles.

Needs matplotlib and SciencePlots. They are not part of the site build: run this by hand
after changing the data, then commit the SVG it writes beside the CSV.

Usage: python tools/make_charts.py
"""
from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "data" / "figures"

# placeholder colour -> theme name (pages.css: .chart .f-NAME / .s-NAME)
THEME = {"#000001": "fg", "#000002": "dim", "#000003": "c5", "#000004": "c4", "#000005": "c2", "#000006": "c3",
         "#000007": "grid", "#000008": "trace"}
KEEP_ATTRS = ("stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray",
              "stroke-dashoffset", "stroke-miterlimit", "font-size", "text-anchor")


def themed(svg: str, prefix: str = "chart") -> str:
    """Swap placeholder colours for classes and inline style for attributes. Every id gets
    `prefix`, so two charts inlined on one page never share an id."""
    svg = re.sub(r'id="([^"]+)"', lambda m: f'id="{prefix}-{m.group(1)}"', svg)
    svg = re.sub(r'(xlink:href|href)="#([^"]+)"', lambda m: f'{m.group(1)}="#{prefix}-{m.group(2)}"', svg)
    svg = re.sub(r"url[(]#([^)]+)[)]", lambda m: f"url(#{prefix}-{m.group(1)})", svg)
    svg = re.sub(r"<style[^>]*>.*?</style>\s*", "", svg, flags=re.S)
    svg = re.sub(r"<metadata>.*?</metadata>\s*", "", svg, flags=re.S)

    def one(m: re.Match) -> str:
        out, classes = [], []
        for decl in m.group(1).split(";"):
            if ":" not in decl:
                continue
            k, v = (s.strip() for s in decl.split(":", 1))
            if k in ("fill", "stroke") and v.lower() in THEME:
                classes.append(("f-" if k == "fill" else "s-") + THEME[v.lower()])
            elif k in ("fill", "stroke") and v == "none":
                out.append(f'{k}="none"')
            elif k in ("fill", "stroke"):
                raise ValueError(f"colour {v} has no theme: draw it with a placeholder")
            elif k in ("opacity", "fill-opacity", "stroke-opacity"):
                if float(v) < 1:
                    raise ValueError("charts are drawn opaque")
            elif k in KEEP_ATTRS:
                out.append(f'{k}="{v}"')
            elif k == "font":
                size = re.search(r"([\d.]+)px", v)
                if size:
                    out.append(f'font-size="{size.group(1)}"')
            # anything else (font-family, clip and so on) falls back to the page's CSS
        if classes:
            out.append(f'class="{" ".join(classes)}"')
        return " " + " ".join(out) if out else ""

    svg = re.sub(r'\s*style="([^"]*)"', one, svg)
    if "style=" in svg or "<style" in svg:
        raise ValueError("inline style left in the chart")
    svg = re.sub(r"<\?xml[^>]*>\s*|<!DOCTYPE[^>]*>\s*", "", svg)
    # size comes from CSS; keep the viewBox
    svg = re.sub(r'<svg([^>]*?) width="[^"]*" height="[^"]*"', r"<svg\1", svg, count=1)
    return svg.replace("<svg ", '<svg class="chart" aria-hidden="true" focusable="false" ', 1)


def rows(name: str) -> list[dict]:
    with open(FIGS / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(line for line in f if not line.startswith("#")))


def driver_edges(plt, np) -> str:
    data = rows("driver-edges")
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    series = (("rise_a_ns", "rise, output A", "#000003", "o"),
              ("fall_a_ns", "fall, output A", "#000004", "s"),
              ("rise_b_ns", "rise, output B", "#000005", "^"))
    for col, label, colour, marker in series:
        pts = [(float(r["rail_v"]), float(r[col])) for r in data if r[col]]
        x, y = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
        ax.plot(x, y, marker, ms=3.6, color=colour, label=label)
        slope, icept = np.polyfit(x, y, 1)
        xs = np.array([x.min(), x.max()])
        ax.plot(xs, icept + slope * xs, ls="--", lw=0.9, color=colour)
    ax.set_xlabel("Rail measured in each capture (V)")
    ax.set_ylabel("Edge time, 10–90 % (ns)")
    ax.legend(loc="upper left")
    for spine in ax.spines.values():
        spine.set_color("#000001")
    ax.tick_params(which="both", colors="#000001")
    ax.xaxis.label.set_color("#000001")
    ax.yaxis.label.set_color("#000001")
    for t in ax.get_legend().get_texts():
        t.set_color("#000001")
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    return buf.getvalue()


def driver_pdn(plt, np) -> str:
    data = rows("driver-pdn")
    f = np.array([float(r["freq_hz"]) for r in data]) / 1e6
    keep = f >= 1.0
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    for col, label, colour, ls in (("drive_a_ohm", "drive board, output A", "#000003", "-"),
                                   ("drive_b_ohm", "drive board, output B", "#000003", "--"),
                                   ("control_a_ohm", "control board, output A", "#000004", "-"),
                                   ("control_b_ohm", "control board, output B", "#000004", "--")):
        z = np.array([float(r[col]) for r in data])
        ax.plot(f[keep], z[keep], ls=ls, lw=1.0, color=colour, label=label)
    for target in (125, 400):
        ax.axvline(target, ls=":", lw=0.8, color="#000002")
        ax.text(target * 1.06, 0.13, f"{target} MHz", rotation=90, va="bottom", fontsize=9, color="#000002")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(0.1, 3000)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Supply impedance (Ω)")
    ax.legend(loc="upper left", fontsize=9)
    for t in ax.get_legend().get_texts():
        t.set_color("#000001")
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    return buf.getvalue()


def detector_coupling(plt, np) -> str:
    data = rows("detector-coupling")
    f = np.array([float(r["freq_hz"]) for r in data]) / 1e6
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    for col, label, colour, ls in (("no_star_db", "no star ground", "#000004", "-"),
                                   ("no_star_two_chokes_db", "no star ground, two chokes", "#000004", "--"),
                                   ("star_db", "star ground", "#000003", "-")):
        ax.plot(f, [float(r[col]) for r in data], ls=ls, lw=1.1, color=colour, label=label)
    ax.set_xscale("log")
    ax.set_ylim(-120, -60)
    ax.set_xlim(0.5, 2000)
    ax.set_xlabel("Frequency (MHz)")
    ax.set_ylabel("Drive to detector coupling (dB)")
    ax.legend(loc="upper left", fontsize=9)
    for t in ax.get_legend().get_texts():
        t.set_color("#000001")
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    return buf.getvalue()


def gate_blanking(plt, np) -> str:
    data = rows("gate-blanking")
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    for energy, colour, marker in (("10", "#000003", "o"), ("11", "#000005", "s"),
                                   ("14", "#000006", "^"), ("15", "#000004", "D")):
        pts = [(float(r["voltage_v"]), float(r["transmitted"])) for r in data if r["energy_kv"] == energy]
        charge = next(r["charge"] for r in data if r["energy_kv"] == energy)
        ion = r"C$_{60}^{2+}$" if charge.endswith("++") else r"C$_{60}^{+}$"
        ax.plot([p[0] for p in pts], [100 * p[1] for p in pts], marker=marker, ms=2.8, lw=1.0,
                color=colour, label=f"{energy} kV, {ion}")
    ax.axhline(10, ls="--", lw=0.8, color="#000002")
    ax.text(68, 12, "10 %", ha="right", fontsize=9, color="#000002")
    ax.set_xlim(0, 70)
    ax.set_ylim(-3, 105)
    ax.set_xlabel("Gate voltage per channel (V)")
    ax.set_ylabel("Beam transmitted (%)")
    ax.legend(loc="upper right", fontsize=9)
    for t in ax.get_legend().get_texts():
        t.set_color("#000001")
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    plt.close(fig)
    return buf.getvalue()


def _finish(fig, ax) -> str:
    leg = ax.get_legend()
    if leg:
        for t in leg.get_texts():
            t.set_color("#000001")
    fig.tight_layout()
    buf = io.StringIO()
    fig.savefig(buf, format="svg", transparent=True)
    fig.clf()
    return buf.getvalue()


def phd_coding(plt, np) -> str:
    """An illustration, not data: one period of pulsing against an order-5 m-sequence."""
    n = 31
    reg, code = 1, []
    for _ in range(n):                      # Galois LFSR for x^5 + x^3 + 1
        code.append(reg & 1)
        reg = (reg >> 1) ^ (0b10100 if reg & 1 else 0)
    assert sum(code) == 16
    reps = 2
    coded = np.array(code * reps)
    pulsed = np.zeros(n * reps, dtype=int)
    pulsed[::n] = 1
    t = np.arange(n * reps + 1)
    fig, ax = plt.subplots(figsize=(5.0, 2.0))
    for y0, s, colour in ((1.7, coded, "#000003"), (0.0, pulsed, "#000004")):
        ax.step(t, y0 + np.append(s, s[-1]), where="post", lw=1.1, color=colour)
    for k in range(reps + 1):
        ax.axvline(k * n, ls=":", lw=0.7, color="#000002")
    ax.text(0.5, 2.85, "coded: open 16 symbols in 31", fontsize=9, color="#000003")
    ax.text(0.5, 1.15, "pulsed: open 1 symbol in 31", fontsize=9, color="#000004")
    ax.set_xlim(0, n * reps)
    ax.set_ylim(-0.2, 3.3)
    ax.set_yticks([])
    ax.set_xticks([0, n, 2 * n])
    ax.minorticks_off()
    ax.set_xlabel("Time (symbols), two periods")
    for side in ("left", "right", "top"):
        ax.spines[side].set_visible(False)
    out = _finish(fig, ax)
    plt.close(fig)
    return out


def phd_pair_spectra(plt, np) -> str:
    data = rows("phd-pair-spectra")
    t = np.array([float(r["lag_samples"]) for r in data]) / 1e3     # 1 GS/s, so 1,000 samples = 1 µs
    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    ax.plot(t, [float(r["coded_sd"]) for r in data], lw=0.6, color="#000003", label="coded, above")
    ax.plot(t, [-float(r["pulsed_sd"]) for r in data], lw=0.6, color="#000004", label="pulsed, below")
    ax.axhline(0, lw=0.5, color="#000001")
    for s in (4, -4):
        ax.axhline(s, ls=(0, (3, 2)), lw=0.6, color="#000002")
    delta, kappa = 8729.6, 4208.0       # the silver-pair mass scale the thesis assumes
    for lab, mz in (("Na$^+$", 22.990), ("Ag$^+$", 107.9), ("Ag$_2^+$", 215.8), ("Ag$_3^+$", 323.7)):
        ax.text((delta + kappa * np.sqrt(mz)) / 1e3, 0.97, lab, transform=ax.get_xaxis_transform(),
                fontsize=9, ha="center", va="top", color="#000001")
    ax.set_xlim(0, 112)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo * 1.05, hi * 1.15)
    ticks = [v for v in ax.get_yticks() if lo * 1.05 <= v <= hi * 1.15]
    ax.set_yticks(ticks, [f"{abs(v):g}" for v in ticks])
    ax.set_xlabel("Flight time (µs)")
    ax.set_ylabel("Height over baseline noise (s.d.)")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, fontsize=9)
    out = _finish(fig, ax)
    plt.close(fig)
    return out


def phd_speedup(plt, np) -> str:
    data = rows("phd-speedup")
    label = {"Na": "Na$^+$", "107Ag": "$^{107}$Ag$^+$", "109Ag": "$^{109}$Ag$^+$", "Ag2": "Ag$_2^+$",
             "Ag3": "Ag$_3^+$"}
    fig, ax = plt.subplots(figsize=(5.0, 2.8))
    y = np.arange(len(data))[::-1]
    for yi, r in zip(y, data):
        v, lo, hi = float(r["time_ratio"]), float(r["lo"]), float(r["hi"])
        ax.errorbar([v], [yi], xerr=[[v - lo], [hi - v]], fmt="o", ms=4, color="#000003", elinewidth=1.0,
                    capsize=2)
        ax.text(hi * 1.25, yi, f"{v:.0f}×", fontsize=9, va="center", color="#000001")
    top = ax.get_xaxis_transform()
    ax.axvline(1024, ls="--", lw=0.8, color="#000002")
    ax.text(1024, 1.03, "ideal counting, 1,024×", transform=top, fontsize=9, ha="right", va="bottom",
            color="#000002")
    ax.axvline(1, ls=":", lw=0.8, color="#000002")
    ax.text(1, 1.03, "no gain", transform=top, fontsize=9, ha="left", va="bottom", color="#000002")
    ax.set_xscale("log")
    ax.set_xlim(0.8, 2000)
    ax.set_ylim(-0.7, len(data) - 0.3)
    ax.set_yticks(y, [label[r["peak"]] for r in data])
    ax.tick_params(axis="y", which="both", length=0)
    ax.set_xlabel("Times faster to the same signal-to-noise")
    out = _finish(fig, ax)
    plt.close(fig)
    return out


# Sniffer charts. ESP32-C6 draws in the trace colour, nRF54L15 in the RF channel's colour (c2).
C6, NRF = "#000008", "#000005"


def _no_ygrid(ax) -> None:
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", which="both", length=0)
    ax.minorticks_off()


def sniffer_link(plt, np) -> str:
    data = rows("sniffer-link")
    fig, ax = plt.subplots(figsize=(5.0, 2.4))
    y = np.arange(len(data))[::-1]
    for yi, r in zip(y, data):
        v = float(r["kB_per_s"])
        ax.barh(yi, v, height=0.55, color=C6 if r["link"].startswith("ESP") else NRF)
        ax.text(v + 12, yi, f"{v:g} kB/s", va="center", fontsize=9, color="#000001")
    ax.axvline(31, ls="--", lw=0.9, color="#000002")
    ax.text(38, -0.62, "full 802.15.4 channel: about 31", fontsize=9, color="#000002", va="bottom")
    ax.set_yticks(y, [r["link"] for r in data])
    ax.set_xlim(0, 1000)
    ax.set_ylim(-0.7, len(data) - 0.4)
    ax.set_xlabel("Sustained throughput (kB/s)")
    _no_ygrid(ax)
    out = _finish(fig, ax)
    plt.close(fig)
    return out


def sniffer_sweep(plt, np) -> str:
    data = rows("sniffer-sweep")
    x = [int(r["payload_bytes"]) for r in data]
    fig, ax = plt.subplots(figsize=(5.0, 2.8))
    ax.plot(x, [float(r["payload_kB_per_s"]) for r in data], "-o", ms=3.5, lw=1.4, color=C6, label="payload")
    ax.plot(x, [float(r["wire_kB_per_s"]) for r in data], "--s", ms=3, lw=1.2, color=NRF,
            label="on the wire, with headers")
    ax.set_xscale("log", base=2)
    ax.set_xticks(x, [str(v) for v in x])
    ax.minorticks_off()
    ax.set_ylim(600, 850)
    ax.set_xlabel("Payload bytes per packet")
    ax.set_ylabel("kB/s")
    ax.legend(loc="lower right", fontsize=9)
    out = _finish(fig, ax)
    plt.close(fig)
    return out


def sniffer_timing(plt, np) -> str:
    data = rows("sniffer-timing")
    fig, ax = plt.subplots(figsize=(5.0, 2.9))
    j = next(r for r in data if r["kind"] == "jitter")
    v, lo, hi = float(j["us"]), float(j["lo_us"]), float(j["hi_us"])
    ax.barh(0.75, hi - lo, left=lo, height=0.16, color=C6)
    ax.plot([v], [0.75], "o", ms=6, color="#000001")
    ax.text(hi * 1.4, 0.75, f"{v:g} µs jitter", va="center", fontsize=9, color="#000001")
    for r in (r for r in data if r["kind"] == "ref"):
        ref = float(r["us"])
        when = f"{ref / 1000:g} ms" if ref >= 1000 else f"{ref:g} µs"
        ax.axvline(ref, ls="--", lw=0.9, color="#000002")
        ax.text(ref / 1.12, 0.04, f"{r['label']}, {when}", rotation=90, ha="right", va="bottom", fontsize=9,
                color="#000002")
    ax.set_xscale("log")
    ax.set_xlim(0.1, 30000)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xticks([0.1, 1, 10, 100, 1000, 10000], ["0.1 µs", "1 µs", "10 µs", "100 µs", "1 ms", "10 ms"])
    _no_ygrid(ax)
    out = _finish(fig, ax)
    plt.close(fig)
    return out


def sniffer_ble_error(plt, np) -> str:
    data = rows("sniffer-ble-error")
    fig, ax = plt.subplots(figsize=(5.0, 2.2))
    y = np.arange(len(data))[::-1]
    for yi, r in zip(y, data):
        lo, hi = float(r["p1_us"]), float(r["p99_us"])
        ax.barh(yi, hi - lo, left=lo, height=0.42, color=C6 if r["board"] == "ESP32-C6" else NRF)
        ax.text(lo - 1.5, yi, f"{lo:+g}".replace("-", "−"), ha="right", va="center", fontsize=9, color="#000001")
        ax.text(hi + 1.5, yi, f"{hi:+g}", ha="left", va="center", fontsize=9, color="#000001")
    ax.axvline(0, lw=0.8, color="#000001")
    ax.set_yticks(y, [f"{r['board']}\n{r['events']} events" for r in data])
    ax.set_xlim(-45, 55)
    ax.set_ylim(-0.6, len(data) - 0.4)
    ax.set_xlabel("Timestamp error, 1st to 99th percentile (µs)")
    _no_ygrid(ax)
    out = _finish(fig, ax)
    plt.close(fig)
    return out


def sniffer_carrier(plt, np) -> str:
    data = rows("sniffer-carrier")
    v = [float(r["median_dbm"]) for r in data]
    fig, ax = plt.subplots(figsize=(5.0, 2.6))
    ax.step(range(len(v) + 1), v + [v[-1]], where="post", lw=1.6, color=C6)
    for i, (r, d) in enumerate(zip(data, v)):
        ax.text(i + 0.5, d + 2.5, f"{d:g} dBm".replace("-", "−"), ha="center", fontsize=9, color="#000001")
    ax.annotate("", xy=(1.5, v[1] - 1), xytext=(1.5, v[0] + 1),
                arrowprops={"arrowstyle": "<->", "color": "#000002", "lw": 0.9})
    ax.text(1.58, (v[0] + v[1]) / 2, f"+{v[1] - v[0]:g} dB", va="center", fontsize=9, color="#000002")
    ax.set_xticks([0.5, 1.5, 2.5], [r["state"] for r in data])
    ax.tick_params(axis="x", which="both", length=0)
    ax.set_xlim(0, 3)
    ax.set_ylim(-112, -60)
    ax.set_ylabel("Channel 20, median (dBm)")
    ax.grid(axis="x", visible=False)
    ax.minorticks_off()
    out = _finish(fig, ax)
    plt.close(fig)
    return out


def sniffer_fuzz(plt, np) -> str:
    data = rows("sniffer-fuzz")
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    y = np.arange(len(data))[::-1]
    for yi, r in zip(y, data):
        n = int(r["inputs"])
        ax.barh(yi, n, height=0.6, color=C6)
        ax.text(n * 1.15, yi, f"{n:,}", va="center", fontsize=9, color="#000001")
    ax.set_xscale("log")
    ax.set_xlim(100, 100000)
    ax.set_xticks([100, 1000, 10000, 100000], ["100", "1,000", "10,000", "100,000"])
    ax.set_yticks(y, [r["target"] for r in data])
    ax.set_xlabel("Random inputs per run (log scale)")
    _no_ygrid(ax)
    out = _finish(fig, ax)
    plt.close(fig)
    return out


CHARTS = {"driver-edges": driver_edges, "driver-pdn": driver_pdn, "detector-coupling": detector_coupling,
          "gate-blanking": gate_blanking, "phd-coding": phd_coding, "phd-pair-spectra": phd_pair_spectra,
          "phd-speedup": phd_speedup, "sniffer-link": sniffer_link, "sniffer-sweep": sniffer_sweep,
          "sniffer-timing": sniffer_timing, "sniffer-ble-error": sniffer_ble_error,
          "sniffer-carrier": sniffer_carrier, "sniffer-fuzz": sniffer_fuzz}


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import scienceplots  # noqa: F401  (registers the "science" style)

    plt.style.use(["science", "no-latex"])
    plt.rcParams.update({
        "svg.fonttype": "none",   # real text, set in the page's own sans
        "svg.hashsalt": "portfolio",
        "font.family": "sans-serif", "font.size": 10, "legend.fontsize": 9,
        "axes.grid": True, "axes.axisbelow": True, "grid.color": "#000007", "grid.linewidth": 0.5,
        "grid.linestyle": "-",
        "legend.frameon": False, "axes.linewidth": 0.6,
        "text.color": "#000001", "axes.edgecolor": "#000001",
        "xtick.color": "#000001", "ytick.color": "#000001", "axes.labelcolor": "#000001",
    })
    for name, draw in CHARTS.items():
        (FIGS / f"{name}.svg").write_text(themed(draw(plt, np), name), encoding="utf-8", newline="\n")
        print(f"wrote data/figures/{name}.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
