+++
title = "UDeep: figures that keep more of the data"
description = "A draft standard for scientific figures that show values brighter than white on HDR screens."
[extra]
start = "2026-10"   # placeholder from the repo's first commit: Mathew to confirm
end = "now"
featured = false
milestone = false
role = false
skills = ["Python", "Rust", "Julia", "HDR imaging", "open standards"]
text_only = false
hero = "sun-sdr.png"
hero_alt = "The Sun in extreme ultraviolet, with a colour bar marking where ordinary white ends"
my_part = "I wrote the draft standard with AI coding agents helping. Its tools are in Python, Rust, JavaScript or Julia."
result = "Values above a chosen level appear brighter than white on an HDR screen, while the ordinary figure stays as it was. The file states how the data became light, so a figure can be checked, inverted or reproduced."
[[extra.readouts]]
label = "tools"
value = "4 languages"
[[extra.readouts]]
label = "format"
value = "open draft"
[[extra.proof]]
kind = "code"
label = "Code on GitHub"
url = "https://github.com/ultradeeprange/udeep"
[[extra.proof]]
kind = "document"
label = "The draft standard, with examples"
url = "https://ultradeeprange.github.io/udeep/"
+++

## Why I built it

An ordinary figure holds 256 levels and stops at white, so it throws away much of the measurement
behind it. I wanted figures that keep more of that range and say in the file how the data became
brightness. I couldn't find a standard for that, so I started one.

## Photos

{{ <figure src="sun-sdr.png" alt="The Sun in extreme ultraviolet, with a colour bar marking where ordinary white ends" caption="An example from the draft, as an ordinary figure. On an HDR screen the brightest loops rise above white. Data: NASA/SDO." /> }}
