+++
title = "PhD: a faster time-of-flight instrument"
description = "A new way to switch the ion beam of a time-of-flight mass spectrometer, from the gate to the data."
sort_by = "weight"
[extra]
still_to_come = ["photos"]
still_to_come_note = "Photos follow once the thesis is submitted."
start = "2017-09"
end = "2024-03"
featured = true
milestone = true
role = false
study = true
bus_label = "PhD"   # its label on the D1 study line
skills = ["time-of-flight mass spectrometry", "signal processing", "signal integrity", "EMI and grounding"]
text_only = false
hero = "biotof.jpg"
hero_alt = "The BioTOF instrument in its lab: a stainless-steel vacuum chamber on a steel table with tall columns for the ion guns"
my_part = "I designed the gate that switches the beam and the 150 V driver behind it. I built the 1 GS/s capture that records the result. Then I found out why the first data looked flat."
result = "In a matched test on the instrument, the modulated beam reached conventional pulsing's signal-to-noise about 30 times faster for the strongest line."
# Key figures, drawn from the parts.
[[extra.readouts]]
label = "edge"
value = "1.3–1.8 ns"
[[extra.readouts]]
label = "finest gate wires"
value = "50 µm"
[[extra.readouts]]
label = "capture"
value = "1 GS/s"
[[extra.readouts]]
label = "speed-up"
value = "~30× faster"
[[extra.proof]]
kind = "data"
label = "Supplementary data and figures"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/"
[[extra.proof]]
kind = "document"
label = "Thesis chapters"
on_request = true   # the thesis is not yet submitted
[[extra.proof]]
kind = "data"
label = "Simulation: when multiplexing beats pulsing"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/multiplex-acquisition/"
+++

## In brief

A time-of-flight secondary ion mass spectrometer tells you what a surface is made of, molecule
by molecule, in its top few nanometres. Instruments like it are used to:

- find [metal contamination on silicon wafers](https://www2.avs.org/symposium1999/Papers/Paper_AS-FrM6.html)
- profile the [layers that grow inside lithium batteries](https://pmc.ncbi.nlm.nih.gov/articles/PMC11790834/)
- study where [bone meets a titanium implant](https://research.chalmers.se/en/publication/83810)
- map [drugs inside single cells](https://pmc.ncbi.nlm.nih.gov/articles/PMC10483116/)
- read the [pigments and binders in old paintings](https://hal.science/hal-03537014)
- tell [whether a fingerprint was left before or after the ink](https://rke.abertay.ac.uk/en/publications/determining-the-chronology-of-deposition-of-natural-fingermarks-a/) on a printed page
- analyse [dust from comet 67P](https://www.mps.mpg.de/en/rosetta/cosima), on board the Rosetta spacecraft

Its weakness is speed. To time the ions it lets the beam through in short bursts, so the beam is
off almost all of the time. In the pulsed run of my matched test the gate was open for
just 0.049% of it. Nearly all of the beam goes unused.

My PhD asked whether the beam could stay on half the time without losing the timing, by switching
it in a coded pattern and decoding the result. I built the hardware to do that on a real
instrument, the BioTOF at the University of Manchester. I also built the software to read it
back.

It worked. In a matched test the coded beam gave the same spectrum, with the same peaks in the
same places, about 30 times faster. Just as useful, the work shows where the method pays off:
when time is the limit rather than damage to the sample. It also measures what the gate, the beam
and the electronics each cost. The data, figures and simulations are public on the supplementary
site. The PhD was funded by a joint award from EPSRC and a University of Manchester Presidential Doctoral Scholarship.


## What the instrument does

A time-of-flight secondary ion mass spectrometer fires a beam of ions at a sample. It then times
how long the ions knocked out of the sample take to reach a detector, which tells you their mass.

Conventional pulsing lets the beam through in short bursts, so it is off for almost all of the
time. My PhD tried another way: switch the beam in a known pattern that keeps it on about half
the time, then recover the spectrum from the pattern. That raises the duty cycle from 0.049% in my pulsed test
towards 50%.

## The question

The idea is the multiplex advantage behind Fourier-transform and Hadamard spectroscopy. The
pattern was an m-sequence, a pseudo-random code. Decoding correlates the detector's record with
the code, which turns the overlapping arrivals back into one spectrum. With the gate open 1,024
times as long, ideal counting would give 32 times the signal-to-noise, or the same spectrum in
about a thousandth of the time. The question was how much of that survives on a real
instrument. And if not all of it, what takes the rest?

## The test

On 7 September 2022 I recorded a matched pair, ten minutes apart, through the same gate and
driver on the same silver sample. One run played an order-11 m-sequence, open 50.0% of the time.
The other opened the gate once per period of the same length, 0.049% of the time.

## What it showed

The decoded spectrum is the same spectrum. The lines sit where the pulsed run puts them, with the
same widths: a resolving power of about 160 at silver-107 in both, on the mass scale fitted to the silver lines. The two silver isotopes keep
their ratio to within about 10%.

It is faster. Every line reached a given signal-to-noise in less time, from 11 times faster for
the weakest line to 33 times for silver-109. Silver-107 came out 32 times faster (29 to 36).
At equal time, the smallest detectable line was 2.7 times weaker.

It is not a thousand times faster. The data say why. Decoding spreads every ion's counting
noise across the whole spectrum. So a line gains only as the square root of its share of all the
counts. Silver-107 was about 3% of the events, so it realised about 3% of the ideal saving. Events
that carried no trace of the code cost a further 1.7 times. Those could in principle be stopped before the
detector. The noise from the rest of the spectrum can't, because every species is coded the same way.

The gain is in time, not dose. At the same beam current the coded beam would put 1,024 times the dose on the sample. Per unit
of dose, pulsing extracts more from each ion: the coded run's figure is 0.18 to 0.67 of the
pulsed one. So the method suits work limited by time rather than by damage: metals, depth
profiling and C60 analysis of organics where the damage clears as fast as it builds. It also
suits continuous beams and spectra dominated by a few strong lines.

The pair has limits. Only the set points were recorded, not the
beam current or drive voltage actually delivered, so the dose figures are inferred. The pulsed run repeated at the coded run's long
period. Had it run at its own fastest rate, the advantage is projected to fall to 17 to 20
times. A clean test needs both arms in one run, with the current logged.

A simulation built on the measured gate shows what a better one needs. Below 0.3% leakage when
shut, the gate keeps 99% of the ideal. The biggest loss is the events the code never touched.
That is a property of the beam, not the gate.

## On the instrument

The work ran from metal to data, so it is split into the six parts listed above. I also
commissioned the electronics on the live instrument, fixing EMI and ground-loop problems.

I'm a PhD candidate at the University of Manchester. The thesis is not yet submitted.
