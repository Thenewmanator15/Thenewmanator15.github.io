+++
title = "Decoding the signal"
description = "Turning a coded record back into a spectrum: which decode to trust, where the gate's echoes come from."
weight = 6
[extra]
skills = ["signal processing", "Julia", "Python"]
[[extra.proof]]
kind = "data"
label = "Simulation: when multiplexing beats pulsing"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/multiplex-acquisition/"
[[extra.proof]]
kind = "document"
label = "Decode comparison and scorecard"
on_request = true
+++

## What a coded record looks like

A coded run looks like noise. One order-11 run held 9.1 million detected ions in 10 captures.
Folded at the code's period, they spread over every bin and no line stood out. But the scatter
between bins was 77 events, against 33 for counting alone. Folded at a wrong period, the same
events scattered by 33. That excess is the spectrum, written into the record by the code.
Correlating the fold with the code brings it back. All five runs gave the same lines at the same
flight times.

## Three decodes that are one

The correlation, the fast m-sequence transform and an inverse filter through the FFT gave the
same spectrum, to within about one part in 10¹⁵ of the peak. So choosing between them is a question of
speed, not of information.

## The echoes

The simple decode left a negative copy behind every line, about 4% of its size (2.5 to 6.8%
from run to run). That is the signature of beam lost each time the gate opens or closes.

Telling the decode about the driver's measured edges didn't help: the copy stayed at 4.4%. Nor
did a wider beam. A lossy-edge model did. It shortens each open run and dims the symbol after a
closed one. I fitted its three numbers on one run and carried them unchanged to the other four.
The median copy fell to 0.4% with no loss of sensitivity, though run by run it ranged up to 2%. The caveat is that the model was fitted to the
copies it removes. On a run from a different day it overcorrected, so it describes that day's
gate, not the gate in general.

The driver isn't where most of the loss arises. Its bench edges predict at most 1.7 samples lost
at each transition. The ions imply about 5. So the drive accounts for a third at most. The rest
happens in the gate or the beam.

## Resolution against sensitivity

A Wiener decode inverts the code instead of correlating with it. With the lossy-edge model it
fully resolved the two silver isotopes, narrowed the silver-107 line from 56 to 36 samples and
left no copy. The price was sensitivity: the line's area over noise fell to 0.84 of the simple
decode's.

Methods that force the spectrum to be non-negative drew every line sharper. But in simulation a
line 1/100 the size of the largest came back at only 3 to 12% of its true size. Small lines
weren't measured badly; they were set to zero. A sharper picture isn't a better estimate.

So the choice depends on the question. To find lines and measure their areas, use the
equalised decode. To separate close lines or measure their ratios, use the Wiener decode. Keep
the simple decode as the reference, because it assumes nothing beyond the code that was played.

## Fixing the echoes at the source

A decode can only undo what it's told about. The better fix is a code that is immune. An
inverse-repeat sequence plays the m-sequence, then its complement with every symbol flipped. The
copies change sign between the two halves but the lines don't, so averaging the halves cancels
the copies.

In simulation through the fitted gate, the copy fell from 6.3% to 0.05%, with no loss of
signal-to-noise. Half the difference of the two halves cancels the lines instead and leaves the
copy. So every run would measure its own gate's loss, with no calibration run and no fitted
model. This is simulated, not yet run on the instrument.
