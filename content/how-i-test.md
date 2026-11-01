+++
title = "How I test"
description = "Hardware or software, the same habits: automate early, sweep the whole range, hold still what affects the result."
+++

I test hardware and software the same way.

## Automate from the start

People can't always be there to spot a small change in a long run of data, so the system has to
catch it. On my PhD the test bench ran its experiments in the loop by itself (see
[capture and timing](@/instruments/phd/capture.md)).

## Sweep the whole range

In hindsight I'd have spent more of my PhD on automated sweeps, mapping the driver's whole
operating range instead of testing it point by point. Now I characterise the full range first.

## Hold still what affects the result

A comparison is only fair when the things that change the result are held still: the clock, the
temperature, the load on the machine. When I
tested the [driver's shield](@/instruments/phd/emi.md), I also moved only the supply cable, as a
control. It changed the reading by 0.6 dB, against 5 to 9 dB for the shield.

## Check the result is real

Before I trust a result, I try to break it: independent slices of the data, decoy inputs,
settings that should give nothing. [The timing problem](@/instruments/phd/timing-problem.md) is
the longest example.
