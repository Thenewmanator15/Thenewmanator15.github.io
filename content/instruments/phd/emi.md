+++
title = "Grounding and EMI"
description = "Tracing how the driver's switching noise reached the detector: what stopped it, what made it worse."
weight = 4
[extra]
skills = ["EMI and grounding", "VNA measurements", "signal integrity"]
[[extra.proof]]
kind = "data"
label = "All twelve coupling measurements"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/detector-coupling/"
[[extra.proof]]
kind = "measurements"
label = "Near-field scans of the driver shield"
on_request = true
+++

## The problem

The driver switches up to 150 V in under 2 ns. On the same instrument, the detector counts single ions as
pulses a few millivolts high. In 2021 the driver's switching noise was turning up in the
measurements, so I set out to find the path it took and close it.

## Finding the path

I measured the coupling from each drive channel into the detector's output with a two-port
vector network analyser, from 9 kHz to 2 GHz. I ran it in twelve configurations. Each
combined the star ground on or off with no, one or two clip-on chokes on the detector cable.

The star ground is a single point bonding the electronics' signal ground to the instrument's
earth. It did the work. Between 10 and 40 MHz it cut the coupling from −73 dB to −111 dB, about
38 dB. Two chokes without it gained only 3 dB.

{{ <chart name="detector-coupling" alt="Plot of coupling from drive channel B into the detector against frequency, 0.5 MHz to 2 GHz. Without the star ground the coupling sits near minus 73 dB from 10 to 40 MHz. Two chokes barely lower it. With the star ground it falls to about minus 111 dB. Above about 100 MHz all three meet near minus 88 dB." caption="Coupling from drive channel B into the detector output, October 2021, smoothed. The star ground does the work below 100 MHz; the chokes barely move it." /> }}

The ferrites' datasheet explains the chokes. Below 20 MHz they present only tens of ohms,
almost all of it reactive. They only turn lossy above about 50 MHz. Above 100 MHz every
configuration met at about −88 dB. So the star point is a low-frequency earth, not an RF
ground. With it in place the direct path from driver to detector was no longer a route that
mattered.

## The shield that made it worse

I also built a shield around the driver: copper tape and a graphite-nickel sheet over a Perspex
former, under Kapton, bonded through posts to the board's metal backing. A near-field probe held
over the driver measured the result on both channels, about 20 minutes apart. The shield made
emission worse. From 120 to 250 MHz it rose by 5 to 9 dB. At 200 MHz it rose by 14 dB. Moving
the supply cable changed it by only 0.6 dB, so the source was the board, not the cable.

The likely cause is the bond. The shield joined the board only through the star point, which is
a long, inductive path at 200 MHz. So the shield floated and re-radiated. The sheet I chose as an
absorber is also a conductive gasket material, which reflects rather than absorbs. That
explanation fits every number, but a bond-impedance measurement would be needed to prove it.

The same scans picked out the driver's own design. Turn-off coupled about 1.7 times harder than
turn-on. That matches the split gate drive: 1 Ω on turn-off against 7.5 Ω on turn-on, so the
turn-off edge is faster and radiates more.

## Everything else

- EMI filters (Murata BNX023) on the driver's supply inputs, rated to 100 V.
- Ferrites on the long coax runs.
- The detector amplifier's bias feed wound twice through a toroid at the supply. The mains leads
  through toroids too.
- A linear supply for the detector amplifier in place of a switch-mode wall adapter.

## Measuring the load

The same campaign measured the gate as the driver sees it. Splitting the two-port into
its differential and common modes gives about 30 pF between the electrodes. From the pair to
the shield it is about 95 pF. Each electrode has about 48 pF to the shield and 5 to 6 pF to the other.
The two channels match to 0.2 dB, within the driver's 100 pF requirement.

## What I'd do differently

I'd measure the coupling before buying the fix, then choose a ferrite that is lossy in the band
of the problem. I'd bond any shield to the chassis with short, wide straps at many points. And
damping needs a lossy element, not just another conductor.
