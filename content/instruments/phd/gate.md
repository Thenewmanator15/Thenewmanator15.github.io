+++
title = "The gate"
description = "A Bradbury–Nielsen gate that switches the ion beam, measured for how well it blanks."
weight = 1
[extra]
still_to_come = ["photos"]
still_to_come_note = "Photos follow once the thesis is submitted."
skills = ["CST", "VNA measurements", "test automation"]
[[extra.proof]]
kind = "photos"
label = "Microscope image of the wires"
to_come = true
[[extra.proof]]
kind = "document"
label = "CST model screenshots"
on_request = true
[[extra.proof]]
kind = "data"
label = "Every blanking sweep, interactive"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/beam-blanking/"
[[extra.proof]]
kind = "data"
label = "S-parameters of three built gates"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/bng-sparams/"
[[extra.proof]]
kind = "data"
label = "Height map of a gate die"
url = "https://thenewmanator15.github.io/mptofsims-supplementary/bng-height/"
+++

## How it works

A Bradbury–Nielsen gate is a grid of fine parallel wires across the beam. With no voltage
between neighbouring wires, the ions fly straight through. With opposite voltages on alternate
wires, they are pushed aside, so the beam is off.

## What I did

I designed gates with 50 µm features. I modelled them in CST, first for the ions' paths, then
for the signal travelling along the wires. I checked the built gates with a vector network
analyser.

## How well it blanked

Over a fortnight in July 2022 I swept the gate voltage while reading the beam current on a
Faraday cup. I ran four beam energies from 10 to 15 kV, with singly and doubly charged C60. Every
voltage step cycled through three drive settings: both electrodes driven, then each alone. The
gate in these sweeps was a larger design than the 50 µm ones, at 150/150 µm.

{{ <chart name="gate-blanking" alt="Plot of beam transmitted, in per cent, against gate voltage per channel from 0 to 70 V, for 10, 11, 14 and 15 kV beams. Each curve falls from 100 per cent towards zero. A dashed line marks 10 per cent, reached at about 19 V for 10 kV. The 14 kV and 15 kV beams reach it at about 27 V." caption="Beam transmitted through the gate against voltage per channel, both electrodes driven, one sweep per energy, 19 to 22 July 2022." /> }}

With both electrodes driven, the gate let through 10% of the beam at about 21 V per channel at
10 kV. At 15 kV it needed about 27 V. Faster ions need a stronger field to turn aside, so the
voltage rose with energy. The charge state made little difference, within about a tenth, as the physics predicts: the
charge cancels between the gate's push and the beam's energy.

The three drive settings made a built-in check. A single electrode needed about twice the
voltage of the pair (1.97 times), as two electrodes driven in opposition should. That check
also caught an earlier analysis, which had averaged the three settings together and overstated
the voltage by about a factor of two. The two electrodes were not equal, though: alone, one
needed 1.7 times the pair's voltage and the other 2.2 times. The voltage monitors tracked both
to within 0.08 V, so the drive was even. The beam or the aperture was off-centre in the gate.

Three more findings change how a gate like this should be specified.

The tail costs the most. At 15 kV, 10% transmission took 27 V but 1% took 50 V. For a modulator
it's that tail, not the bulk of the beam, that sets the voltage.

The gate drifted. At 15 kV it needed 27 V on 22 July. Four days later, a sweep at the same energy needed 55 V.
Nothing in the records explains it, so no figure can be averaged over the whole campaign.

The cup's zero matters. With the beam fully deflected, the cup still read −5 to −6 pA. Not
subtracting that understates the voltage the gate needs.

A coarser 100/200 µm gate, measured in October, needed 56 V at 10 kV against 19 to 26 V for
the 150/150 µm one, about 2.2 times. That's the direction the design predicts. But the two were
measured three months apart. The drift above is just as large. So I don't put the difference down
to wire size alone.

## What went wrong

In May 2022, loose polyimide tape was found partly blocking the gate's aperture. Replacing the
gate cleared the beam path.
