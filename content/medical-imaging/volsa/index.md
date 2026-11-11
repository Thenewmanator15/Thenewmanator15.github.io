+++
title = "Volsa: a desktop MRI and CT viewer"
description = "A desktop viewer for MRI and CT scans, written in Rust with GPU shaders."
[extra]
start = "2026-10"   # placeholder from the repo's first commit: Mathew to confirm
end = "now"
featured = true
milestone = false
role = false
skills = ["Rust", "WGSL", "ONNX Runtime", "DICOM"]
text_only = false
hero = "volsa-planes.jpg"
hero_alt = "Volsa showing a made-up test ball in three planes beside a 3D view, with a ruler, an angle and a region measured on it"
my_part = "I wrote it, with AI coding agents helping: the viewer, the GPU shaders that draw the slices, the brain labelling."
result = "It opens a scan export, then shows it as slices, three planes or a 3D volume you can measure on. It is not a medical device."
[[extra.readouts]]
label = "views"
value = "3 planes + 3D"
[[extra.readouts]]
label = "labels"
value = "on your machine"
[[extra.proof]]
kind = "photos"
label = "Screenshots"
url = "#photos"
[[extra.proof]]
kind = "code"
label = "Code on GitHub"
url = "https://github.com/Thenewmanator15/volsa"
[[extra.proof]]
kind = "code"
label = "Volsa for Windows, the latest release"
url = "https://github.com/Thenewmanator15/volsa/releases/latest"
+++

## Why I built it

I wanted to look at my own brain scan. A lot of scientific software gets little love from
programmers and is left with old interfaces. I wanted the opposite: a viewer written in Rust that
opens a scan quickly, with code that anyone can read and contribute to.

## Labels you can check

Volsa can label brain structures on your own machine, so the scan never leaves it. Each label
comes with the model's own quality check, so you know how far to trust it.

## Photos

{{ <figure src="volsa-planes.jpg" alt="Volsa showing a made-up test ball in three planes beside a 3D view, with a ruler, an angle and a region measured on it" caption="Volsa with a made-up test phantom, not patient data." /> }}
