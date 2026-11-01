+++
title = "Capture, timing and the pattern"
description = "The 1 GS/s capture, the pattern generator, a clock reference board, a detector pre-amplifier, picoamp currents and a vibration rig."
weight = 3
[extra]
still_to_come = ["photos"]
still_to_come_note = "Photos follow once the thesis is submitted."
skills = ["FPGA", "LabVIEW", "clock jitter", "low-noise amplifiers", "low-current measurement", "test automation"]
[[extra.proof]]
kind = "photos"
label = "Photo of the vibration measurement"
to_come = true
[[extra.proof]]
kind = "measurements"
label = "Scope captures and jitter measurements"
on_request = true
[[extra.proof]]
kind = "data"
label = "Clock reference jitter"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/clock-reference/"
[[extra.proof]]
kind = "data"
label = "Capture sample rate against single-ion pulses"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/capture-sampling/"
[[extra.proof]]
kind = "data"
label = "Single-ion pulses, raw and amplified"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/single-ion-events/"
[[extra.proof]]
kind = "data"
label = "The inverting transformer in the detector chain"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/ja4220/"
[[extra.proof]]
kind = "data"
label = "Beam-current averaging"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/beam-averaging/"
[[extra.proof]]
kind = "data"
label = "Vibration spectra"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/vibration-psd/"
+++

## Capture

The capture used a source-synchronous 16-bit ADC and DAC card in a PC, sampling at 1 GS/s. I
changed the FPGA firmware, then wrote the LabVIEW software that recorded 4 s bursts, compressed
with Blosc.

## Timing

I designed an external clock reference board around a 100 MHz oven-controlled crystal
oscillator. It has a low-jitter buffer, three LT3045 regulators in parallel and a monitor on the
oven current that shows when the oscillator has warmed up.

I measured its jitter and phase noise at the picosecond level. From 12 kHz to 20 MHz the jitter
came out at 2.4 ps, but that was the oscilloscope's floor: the oscillator's own figure is
below 0.1 ps, beyond what I could measure.

The reference doesn't clock the converters directly. It disciplines a jitter cleaner on the
converter card, which makes the 1 GHz sample clock. I traced that chain through the card's
firmware and modelled its loop. The vendor's loop filter left the loop under-damped, at about
20° of phase margin, for roughly 200 fs of jitter where a redesigned filter would give about
90 fs. Either way the ADC's own 120 fs aperture jitter is comparable, so a quieter reference
would buy nothing. Those figures are modelled, not measured.

## Generating the pattern

The gate's pattern came from the same card: an FPGA driving a 16-bit DAC at 1 GS/s. In the
firmware a Galois shift register produced the m-sequence one bit per symbol. A controller could
load new taps in one clock cycle, for any sequence order from 3 to 20. An upsampler then held
each bit for a whole number of samples, so symbols could be any width from 16 ns in 1 ns steps.
A FIFO carried the pattern from the FPGA's 250 MHz fabric into the DAC's clock.

I sized the sequences so one full pass fitted within a millisecond, the instrument's 1 kHz limit
on extraction pulsing. At the 50 to 100 ns symbols used, that meant orders 10 to 13, with a pass
of 0.05 to 0.8 ms.

For pulses shorter than 16 ns, I triggered an HP 8082A pulse generator from the card's output.
That covered 2 to 16 ns, at the cost of a 7 ns delay.

The generator itself was clean. Measured on a 4 GHz oscilloscope, its whole timing error was
14 to 20 ps rms. Even that was the oscilloscope's floor. The driver's output, measured with coded
patterns of 19 to 200 ns symbols, reached 33 to 132 ps rms. So the jitter was added after the generator,
most likely in the driver. That is where the effort for a next version should go.

## Pre-amplifier

The detector's pulses are about 2 ns wide and a few millivolts high, so they need amplifying
before capture. The first amplifier, an off-the-shelf pulse amplifier, picked up noise from a
switch-mode wall supply. A linear lab supply fixed that.

I then designed a two-stage amplifier: a programmable-gain differential stage (LMH6881), set
by a rotary switch, into a wideband THS3217 stage. It gave 11 to 15 dB with a bandwidth of
480 MHz. It ran out of headroom for the new capture front end, so I moved to a low-noise
Mini-Circuits amplifier. That gave about 28 dB, sharpened the pulses from 2.0 to 1.6 ns wide and
stayed linear for 98% of ions.

## Low currents

The test bench ran its experiments in the loop by itself. It measured beam currents down to
single-digit picoamps. For those, I used PTFE-insulated cable held under light tension, damped
with foam, so moving cables couldn't make currents of their own.

## Vibration

The C60 ion gun is a heavy mass on a long arm. I mounted an accelerometer on the linear drive to
measure how the instrument shook.
