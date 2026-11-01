+++
title = "The driver"
description = "A gate-driver board that switched up to 150 V with edges of 1.3 to 1.8 ns. It ran to 53 MHz."
weight = 2
[extra]
skills = ["gate drivers", "high-voltage design", "Keysight ADS", "power delivery"]
[[extra.proof]]
kind = "photos"
label = "Photos of the board"
url = "#photos"
[[extra.proof]]
kind = "document"
label = "Board files"
on_request = true
[[extra.proof]]
kind = "measurements"
label = "Driver waveforms"
on_request = true
[[extra.proof]]
kind = "data"
label = "Driver edges across the symbol-width sweep"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/driver-edges/"
[[extra.proof]]
kind = "data"
label = "Where the two channels' mismatch would vanish"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/driver-mismatch/"
+++

## The board

The driver switched up to 150 V differentially with edges of 1.3 to 1.8 ns. It ran to 53 MHz. I designed,
simulated, built and characterised it.

## What it was for

The gate switches the ion beam by putting opposite voltages on alternate wires. The driver makes
those voltages: two outputs, one swinging positive and one negative, switched together in the
pattern that encodes the beam. A symbol in that pattern can be as short as 20 ns, so the edges
had to be fast, the two outputs had to match each other and the timing had to stay steady.

I designed the output stage around that load: the gate and its feedthrough, under 100 pF. The
GaN FETs available then set the ceiling. The small, fast parts I needed were rated to 100 V.
An output on a 75 V rail already overshot to 87 V, so there was no room to push higher.

## How it performed

I measured it against the requirements I set at the start. Each figure is the worst case among
the captures at up to the specified 25 MHz.

| | Target | Measured |
|---|---|---|
| Rise across the gate, 10–90 % | under 2 ns | 1.3 to 1.7 ns |
| Fall across the gate, 10–90 % | under 2 ns | 1.5 to 1.8 ns |
| Jitter | under 200 ps rms | 84 to 120 ps rms |
| Shortest symbol | 20 ns | 19 ns |
| Switching rate | 25 MHz | ran to 53 MHz |
| Swing across the gate | 160 V | 151 V typical, 157 V best |

All but the swing were met. The swing fell about 6% short because the supply rail sagged under
load, so the driver never quite saw its set point. Sensing the rail at the board would fix that.

Past 25 MHz the limit was not edge speed but matching. The two outputs have to cancel each other
away from the gate. That rejection fell from 39 dB at 5 MHz to 20 dB at 53 MHz.

## Rise, fall and skew

Each output on its own switched faster than the pair: 0.9 to 1.5 ns from 24 to 76 V before
tuning, slowing by 5 to 7 ps per volt as the step grew. Output B's rising edge was the fastest
and output A's falling edge the slowest.

The harder part was skew between the two outputs. A trim pot on each pre-driver sets its
timing. On a 4 GHz scope I could tune it to about 50 ps. But the mismatch between the two
outputs moved with drive voltage and with symbol width, so one setting matched only one
combination. For 20 ns symbols it stayed between 0.5 and 2.6 ns across 24 to 79 V, so no
voltage nulled it. I commissioned a second driver tuned for the pattern instead.

{{ <chart name="driver-edges" alt="Scatter plot of edge time against measured rail voltage, 24 to 76 V. Edge times rise from about 0.95 to 1.5 ns, with a straight fitted line for each of three transitions." caption="Edge time on each output against the rail it actually received, before tuning. The edges slow as the step grows, as a slew-rate-limited output should." /> }}

## Layout

I laid it out following signal-integrity principles, using 2D transmission-line simulation in
Keysight ADS. Full-wave CST predicted the waveform at the far end of the gate, through drive-path
parts that had to be safe in vacuum with low capacitance.

{{ <figure src="driver-layout.jpg" alt="Altium layout of the driver's drive board, its top copper in red over the bottom in blue. Two halves mirror each other above and below the centre line. Wide copper paths from each half sweep to the right and meet at the output connectors that feed the gate." caption="The drive board's layout in Altium, version 3.1. The two outputs are laid out as mirror images, so their paths to the gate match." /> }}

## Power delivery

First I chased down the obvious faults. Supply noise was coupling through the isolated DC-DC
converters. The 18 V rail drooped under the load of a capacitor-free LDO. A buck converter
needed more output capacitance before it would regulate.

Then I measured the supply network itself. With a vector network analyser I swept the
impedance of each output's supply from 1 MHz to 1.5 GHz, on the drive board and the control
board separately. The drive board was well decoupled at low frequency, at about 0.6 Ω, but
both outputs had an anti-resonance near 290 MHz that reached about 1 kΩ. The control board's
supplies were much higher at low frequency, with sharper peaks between 110 and 390 MHz.

{{ <chart name="driver-pdn" alt="Log-log plot of supply impedance against frequency from 1 MHz to 1.5 GHz for the drive board and the control board, two outputs each. The drive board starts near 1 ohm and peaks near 1 kilohm at about 290 MHz. The control board is higher at low frequency, with sharper peaks between about 110 and 390 MHz. Dotted lines mark 125 and 400 MHz." caption="Supply impedance of each output on the two boards, November 2021. The dotted lines are the frequencies the new decoupling was chosen for." /> }}

I chose new decoupling for those peaks. Both outputs gained low-inductance C0G capacitors of
2.2 and 4.7 nF. I added 2.7 nF aimed at 125 MHz and 330 pF aimed at 400 MHz. I also found the high-side
gate bias running at 7.4 V against 6.2 V on the low side. I fitted a 6.0 V Zener to bring the two
halves closer, aiming to make them switch more alike. I didn't get to sweep the boards again after these
changes, so how far they flattened the peaks is not measured.

Given more time, I'd have split the control electronics from the high-speed board. Putting
both on one design made each fault harder to isolate. Most failures were on the high-voltage
side.

## Heat

On simple pulses the GaN FETs ran cool. With 100 ns pulses at up to 2 MHz, a thermal camera
showed no real rise over the board's normal temperature. Coded patterns were another matter.
Shorter symbols mean more edges every second. Every edge loses energy in the FETs and the
termination resistors.

| Symbol width | At 45 V | At 70 V |
|---|---|---|
| 100 ns | no real rise | no real rise |
| 50 ns | no real rise | about 70 °C |
| 40 ns | about 80 °C | about 90 °C |
| 20 ns | about 90 °C | about 110 °C |

At 70 V with 20 ns symbols the board passed 110 °C within tens of seconds. I stopped the test
there and ran coded patterns in bursts from then on. The capture software recorded in short
bursts, then spent longer than that processing. That pause let the board cool, which held the
20 ns case at 45 V to about 70 °C. These are camera readings of the board's surface, not junction
temperatures.

The termination resistors reached about 70 °C. The low-side bias diodes and the inductors sat
near 50 °C, which suggests the inductors were a poor choice for the job.

A temperature monitor beside the FETs and a current sense both disable the driver, above about
71 °C or on a short. Testing that showed a flaw: while disabled, the pre-drivers still half-switched the FETs, to about 6 V. So the warning light meant switch off at once.

{{ <figure src="driver-bench-cooling.jpg" alt="The driver on foam on a lab bench, with a black water-cooling radiator beside it and two bench supplies reading 40 V" caption="Bench testing with water cooling, December 2021. The two supplies feed the outputs at 40 V each." /> }}

For the instrument I fitted a water-cooling block and fans to the driver. An earlier drive board
had been built on an aluminium-backed substrate to spread heat. It did, but it drew heat away so
well that reworking parts with hot air was hard.

{{ <figure src="driver-water-block.jpg" alt="A round water-cooling block on an aluminium plate mounted on the vacuum chamber, with coax cables leaving the board beneath" caption="The driver on the instrument with its water-cooling block, October 2022." /> }}

Next time I'd make the high-voltage output a small board of its own beside a cooling element.
I'd also use GaN parts with the temperature sensor on the die, which are now available. They
report the junction temperature directly.

## Photos

{{ <figure src="driver-stack.jpg" alt="Two stacked circuit boards on a blue mat: a black board with a semicircular cutout on top of a green one, with coax cables on gold connectors" caption="The driver on the bench, April 2021: the black power and control board sits on top of the green drive board." /> }}

{{ <figure src="driver-board.jpg" alt="A green circuit board on its own, with inductors, capacitors and gold connectors along its edges" caption="The green drive board on its own, April 2021." /> }}

{{ <figure src="driver-output-stage.jpg" alt="Close-up of a green circuit board showing two black cylindrical parts wrapped in orange tape, with inductors and capacitors around them" caption="The output stage up close, March 2022." /> }}
