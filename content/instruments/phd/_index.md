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


## The problem

A time-of-flight instrument works out each ion's mass from how long it takes to fly to the
detector. To start that clock, the beam is let through in short bursts. Each burst then has to
wait until the slowest ions from the last one have landed. In my pulsed test on the BioTOF that
left the gate open for 0.049% of the time. The other 99.95% of the beam was thrown away. A
measurement took as long as it took to collect enough ions from those short bursts.

{{ <chart name="phd-coding" alt="Two square-wave traces over two periods of 31 symbols. The pulsed trace opens for one symbol at the start of each period. The coded trace switches on and off in an irregular pattern, open for 16 of every 31 symbols." caption="Pulsing against a coded pattern, drawn short so it can be seen. The test used a code of 2,047 symbols, so pulsing opened the gate for 1 symbol in 2,047." /> }}

## The idea

The idea is the multiplex advantage behind Fourier-transform and Hadamard spectroscopy. Keep the
beam on about half the time, switched in a known pattern. The ions from different openings then
overlap at the detector. The pattern was an m-sequence, a pseudo-random code. Because
the code is known, decoding can correlate the detector's record with it and turn the overlapping
arrivals back into one spectrum.

With the gate open 1,024 times as long, ideal counting would give 32 times the signal-to-noise,
or the same spectrum in about a thousandth of the time. The question was how much of that
survives on a real instrument. And if not all of it, what takes the rest?

## The architecture

A coded beam needs a gate that switches in nanoseconds, with a driver to swing it. It needs a
pattern generator to play the code. It also needs a capture fast enough to record single ions
for decoding. I added these as a drive path and a capture path around the instrument.

{{ <chart name="phd-architecture" alt="Block diagram. The drive path runs down the left: a 100 MHz clock reference, a pattern generator playing the m-sequence through a 1 GS/s DAC, the 150 V driver, and the Bradbury–Nielsen gate in the vacuum. The C60 ion beam passes through the gate to the sample, and ions from the sample fly to the detector. The capture path runs up the right: the detector, a bought 28 dB pre-amplifier, a 16-bit 1 GS/s ADC, recording in LabVIEW and decoding in Julia. The pattern generator and the ADC share one converter card with one 1 GHz clock. The clock reference, driver and gate are hardware I designed. The pattern generator, capture, recording and decode are firmware or software I wrote or changed. The pre-amplifier, detector, sample and card are bought or part of the instrument." caption="The system. The pattern generator and the capture sit on one converter card, so the code and the record run from the same clock." /> }}

One card plays the code and records the detector. Both run from the card's 1 GHz clock, which
my 100 MHz reference disciplines, so every sample in the record should line up with a symbol of
the code. In practice the record still slipped against the code, which is
[the timing problem](@/instruments/phd/timing-problem.md).

The code is made in firmware. A Galois shift register produces the m-sequence one bit per
symbol. A controller loads new taps in one clock cycle, for any order from 3 to 20. A symbol can
be any width from 16 ns in 1 ns steps. So a new experiment was a setting, with no file to
build.

The driver was sized to its load. The gate and its feedthrough are under 100 pF. A 20 ns symbol
needs [edges under 2 ns](https://thenewmanator15.github.io/mptofsims-supplementary/driver-edges/) to stay square. I used GaN FETs. The small, fast ones available then were
rated to 100 V. A 75 V rail already overshot to 87 V. So each output stayed at 75 V, one
swinging positive and one negative. Together they put 150 V across the gate.

The detector side is about single ions. [Their pulses](https://thenewmanator15.github.io/mptofsims-supplementary/single-ion-events/)
are about 2 ns wide and a few millivolts high. So they are amplified, then
[sampled at 1 GS/s](https://thenewmanator15.github.io/mptofsims-supplementary/capture-sampling/). The recording stores the raw samples, compressed
without loss. Decoding happens afterwards in software, so the same record can be decoded several
ways and the results compared.

## The clock

I made two choices about the clock. The first was to play the code and record the detector from
one clock. Any drift in the oscillator then moves both together. A symbol is always 100 samples,
so in principle the code and the record can't drift apart, however far the oscillator wanders.
In practice the capture dropped samples after the ADC, which is the timing problem.

The second was an external reference. The card's own oscillator is specified to 10 ppm. The
absolute flight time sets the mass scale, so it needs a steadier source. I designed a reference
board around a 100 MHz oven-controlled crystal oscillator, specified to 2 parts in 10¹¹ over a
second. It has a low-jitter buffer, attenuators to set each output's level and two LT3045
regulators in parallel. A monitor on the oven current shows when the oscillator has warmed up.

{{ <figure src="clock-reference.jpg" alt="A long green circuit board on a wooden desk. A metal-cased oscillator marked OD100LP-61205CV 100.0 MHz sits in the middle with a blue trimmer beside it. Regulators and a power socket are at the top. Below the oscillator a small buffer chip feeds gold traces to two gold SMA connectors at the bottom edge." caption="The clock reference board out of its case. The buffer below the oscillator feeds the two outputs, each through its own attenuator." /> }}

{{ <chart name="phd-clock" alt="Block diagram of the clock chain. My clock reference board, a 100 MHz OCXO, feeds the converter card. On the card a first loop follows the reference below about 100 Hz. A second loop locks a 3 GHz VCO to a 500 MHz VCSO and sets the jitter, about 200 femtoseconds as modelled. Divided by 3, that gives one 1 GHz sample clock, which feeds both the DAC that plays the code and the ADC that records, whose aperture jitter is 120 femtoseconds." caption="The clock chain. My reference disciplines the jitter cleaner on the converter card, which makes one 1 GHz clock for both converters." /> }}

I measured the board on two oscilloscopes with jitter-analysis software. From 12 kHz to 20 MHz
the [jitter came out at 2.4 ps](https://thenewmanator15.github.io/mptofsims-supplementary/clock-reference/). That was the oscilloscope's floor: the oscillator's own figure is
below 0.1 ps. Driving the output harder helped the measurement. At +10 dBm it read 2.4 ps against
4.5 ps at +6 dBm, because a steeper edge turns less amplitude noise into timing noise.

The reference doesn't clock the converters directly. It disciplines a jitter cleaner on the card.
I traced that chain through the card's firmware. The first loop follows the reference only below
about 100 Hz. A second loop locks a 3 GHz oscillator to a 500 MHz one. Divided by three, that
gives the 1 GHz sample clock for both converters. I modelled the second loop with the vendor's
filter. It was under-damped, at about 20° of phase margin, for roughly 200 fs of jitter. A
redesigned filter would give about 90 fs. The ADC's own aperture jitter is 120 fs, so a quieter
reference would buy nothing. Those figures are modelled, not measured.

So the jitter is set on the card, not by my reference. The place to improve it is the card's loop
filter. The reference does the job it's there for: keeping the time of flight steady.

## What I built

Each part has its own page, listed above. I designed, built and tested the driver. I designed
the clock reference board, then measured its jitter. I designed gates, modelled them in CST
and measured how well a gate blanked the beam. I wrote the pattern generator in the card's FPGA.
I changed the card's capture firmware too. I also wrote the recording software and the decode.
Then I
commissioned all of it on the live instrument, which meant fixing ground loops and
[EMI](https://thenewmanator15.github.io/mptofsims-supplementary/detector-coupling/) along the way.

{{ <figure src="driver-layout.jpg" alt="Altium layout of the driver's drive board, its top copper in red over the bottom in blue. Two halves mirror each other above and below the centre line. Wide copper paths from each half sweep to the right and meet at the output connectors that feed the gate." caption="The drive board's layout in Altium, version 3.1. The two outputs are laid out as mirror images, so their paths to the gate match." /> }}

{{ <figure src="driver-stack.jpg" alt="Two stacked circuit boards on a blue mat: a black board with a semicircular cutout on top of a green one, with coax cables on gold connectors" caption="The driver on the bench, April 2021: the black power and control board sits on top of the green drive board." /> }}

{{ <figure src="driver-water-block.jpg" alt="A round water-cooling block on an aluminium plate mounted on the vacuum chamber, with coax cables leaving the board beneath" caption="The driver on the instrument with its water-cooling block, October 2022." /> }}

## How I learned it and checked it

The BioTOF is a commercial instrument that I didn't build. Much of it couldn't be changed,
including the C60 ion gun. Most of the capture card's firmware was the vendor's. On a fixed
budget I had to make design choices before I understood how the instrument worked inside. So I
taught myself the rest as I went. Then I went back and checked those early choices against what
I'd learned.

I learned the gun by testing its beam, since I couldn't change it. I
[swept the gate over a fortnight](https://thenewmanator15.github.io/mptofsims-supplementary/beam-blanking/)
while reading the beam on a Faraday cup, down to single-digit picoamps. I also modelled
the column in CST from Ionoptika's drawing.

I also learned to distrust a result until something had tried to break it.

- The first coded data looked flat, as if the gate had never switched the beam. In 2026 I went
  back to the raw captures. The record ran 2,297 ppm short of the period I'd set, so the fold had
  smeared the signal out. Folded at the measured period, the gate's signal came back. Folded at a
  wrong period on purpose, the same data read nothing. I withdrew the "never modulated" verdict.
- The gate sweeps had a check built in. A single electrode should need twice the voltage of the
  pair. It needed 1.97 times. The same check caught an earlier analysis that had overstated the
  voltage by about a factor of two.
- At 15 kV the gate needed 27 V one day and 55 V four days later. Nothing in the records explains
  it, so I don't average any figure across the campaign.
- The model that removed the decode's echoes was fitted on one run, then carried unchanged to four
  more. On a run from another day it overcorrected. So I report it as a description of that day's
  gate.
- Each figure on these pages says whether it was measured or inferred. The dose figures are
  inferred, for example, because the beam current wasn't logged.

## The test

On 7 September 2022 I recorded a matched pair, ten minutes apart, through the same gate and
driver on the same silver sample. One run played an order-11 m-sequence, open 50.0% of the time.
The other opened the gate once per period of the same length, 0.049% of the time.

## Results

The decoded spectrum is the same spectrum. The lines sit where the pulsed run puts them, with the
same widths: a resolving power of about 160 at silver-107 in both, on the mass scale fitted to the
silver lines. The two silver isotopes keep their ratio to within about 10%.

{{ <chart name="phd-pair-spectra" alt="Mirrored plot of the two spectra against flight time from 0 to 112 microseconds. The coded run is drawn upwards and the pulsed run downwards, each as height over its own baseline noise. Both show lines at the same flight times, labelled sodium, silver, silver dimer and silver trimer, with the silver lines tallest. Dashed lines mark 4 standard deviations." caption="The matched pair, 7 September 2022: coded above, pulsed below, each over its own noise. The pulsed run was recorded for 3.5 times as long. The lines fall in the same places." /> }}

It is faster. Every line reached a given signal-to-noise in less time, from 11 times faster for
the weakest line to 33 times for silver-109. Silver-107 came out 32 times faster (29 to 36).
At equal time, the smallest detectable line was 2.7 times weaker.

{{ <chart name="phd-speedup" alt="Speed-up for five lines on a log scale, each with a 95 per cent interval: sodium 26 times, silver-107 32 times, silver-109 33 times, the silver dimer 11 times and the silver trimer 27 times. A dashed line at 1,024 marks ideal counting. A dotted line at 1 marks no gain." caption="How many times faster the coded run reached the same signal-to-noise, per line, with 95% intervals. Ideal counting would give 1,024." /> }}

It is not a thousand times faster. The data say why. Decoding spreads every ion's counting
noise across the whole spectrum. So a line gains only as the square root of its share of all the
counts. Silver-107 was about 3% of the events, so it realised about 3% of the ideal saving. Events
that carried no trace of the code cost a further 1.7 times. Those could in principle be stopped
before the detector. The noise from the rest of the spectrum can't, because every species is
coded the same way.

The gain is in time, not dose. At the same beam current the coded beam would put 1,024 times the
dose on the sample. Per unit of dose, pulsing extracts more from each ion: the coded run's figure
is 0.18 to 0.67 of the pulsed one.

The pair has limits. Only the set points were recorded, not the beam current or drive voltage
actually delivered, so the dose figures are inferred. The pulsed run repeated at the coded run's
long period. Had it run at its own fastest rate, the advantage is projected to fall to 17 to 20
times. A clean test needs both arms in one run, with the current logged.

## Outcome

The method works on a real instrument. The coded beam gave the same spectrum as pulsing, about
30 times faster for the strongest line. Against pulsing at its own fastest rate, the projection
is 17 to 20 times.

The work also shows where it pays off. Because a line gains with its share of the counts, the
method suits spectra dominated by a few strong lines. Because the gain is in time rather than dose,
it suits work where time is the limit, not damage to the sample: metals, depth profiling and
C60 analysis of organics where the damage clears as fast as it builds. It also suits continuous
beams.

It measures what each part costs, which is what a next version needs to know.

- The gate's tail sets its voltage. At 15 kV,
  [10% transmission took 27 V but 1% took 50 V](https://thenewmanator15.github.io/mptofsims-supplementary/beam-blanking/).
  A [simulation built on the measured gate](https://thenewmanator15.github.io/mptofsims-supplementary/multiplex-acquisition/) shows that below 0.3% leakage when shut, the gate keeps
  99% of the ideal.
- The biggest loss is the events the code never touched. That is a property of the beam, not
  the gate.
- Each line left a negative copy about 4% of its size, from beam lost every time the gate opens or
  closes. The driver accounts for a third of that at most. An inverse-repeat code cancels the
  copy: in simulation it fell from 6.3% to 0.05% with no loss of signal-to-noise.
- Most of the timing error is added after the pattern generator, most likely in the driver: 14 to
  20 ps rms at the generator against 33 to 132 ps rms at the driver's output.
- The driver's high-voltage stage should be a small board of its own beside a cooling element,
  with GaN parts that report their own junction temperature.

I'm a PhD candidate at the University of Manchester. The thesis is not yet submitted.
