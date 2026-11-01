+++
title = "The timing problem"
description = "Why the first results looked flat: a 2,297 ppm timing mismatch."
weight = 5
[extra]
still_to_come = ["proof"]
still_to_come_note = "The cause is strongly indicated but not yet proven on the bench."
skills = ["Julia", "MATLAB", "signal processing"]
[[extra.proof]]
kind = "document"
label = "Fault report"
on_request = true
+++

## Flat results

In 2022 the data, folded at the period I had set, came out flat. It looked as if the gate had not
switched the beam at all.

## The search

In 2026 I went back to the raw captures. AI is a tool I bring in when a problem needs one. This
one did: it helped me build a period search across the files, while I judged what was real.

The search found the gate repeating every 199,541 samples instead of 200,000. Against the
capture, the signal generator looked 2,297 ppm fast.

## Ruling out the rest

I tested the result against itself: three files 30 minutes apart, independent quarters of one
record, decoy patterns or folds at the wrong period. Then I ruled out each other cause in turn:
the converters, the beam, the driver, the detector, the file readers, the PCIe link and the
memory buffer.

## What it points to

The evidence points to the capture firmware dropping about 0.23% of samples where the 250 MHz
stream crosses into a clock derived from PCIe. That cause is strongly indicated, not yet proven
on the bench.

## The result

Folding at the measured period recovered the gate's signal. In a matched test, the modulated
beam reached conventional pulsing's signal-to-noise about 30 times faster for the strongest line.
