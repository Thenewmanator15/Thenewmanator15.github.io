+++
title = "Electronics and embedded engineer, PhovIR"
description = "Firmware and electronics for a handheld spectrometer at a start-up."
[extra]
start = "2025-10"
end = "2025-12"
featured = false
milestone = true
role = true
bus_label = "PhovIR"
text_only = true
skills = ["ESP32", "embedded firmware", "C++", "device drivers", "real-time firmware", "MEMS drive control",
          "test automation", "AI coding agents", "PCB layout review", "photodiode front ends",
          "EMI and grounding", "design for manufacture", "board bring-up", "fault-finding"]
my_part = "I wrote the ESP32 firmware and device drivers, including control of the high-voltage MEMS drive. I led the engineering review of the board layout, then assembled and brought up the boards with the team."
[[extra.proof]]
kind = "photos"
label = "The MIEYRA device, on PhovIR's site"
url = "https://www.phovir.com/mieyra-nir-mir/"
+++

## The company

[PhovIR](https://www.phovir.com/) is a University of Manchester spin-out making a handheld, MEMS-based
infrared (FTIR) spectrometer
([PhovIR on LinkedIn](https://www.linkedin.com/company/phovir-technologies/)). I joined on a
three-month contract to set up the embedded and electronics side, taking the device from an
early concept towards a consumer-ready prototype.

## How we got there

The embedded side started with the ESP32 firmware: drivers for the ADCs and DACs, then control of
the high-voltage MEMS drive. The spectrum depends on the timing between moving the MEMS and
reading the photodiode, so the firmware was interrupt-driven to keep that latency low. A separate
hardware layer left room for MQTT or a web interface later. I wrote it in C++ with AI coding
agents, backed by automated tests. By the end of my contract, readings
were coming through to a console window.

While the first boards were being laid out, I led the engineering review. Placement started at
the photodiode, where heat, coupling and leakage decide how clean the signal is. EMC and ease of
production were part of the same review.

Once the boards arrived, we assembled them as a team. Bringing them up was my job, the MEMS drive
included, as was fault-finding at board and system level. What we found went into the next
revision.

## The device, on PhovIR's site

PhovIR's [MIEYRA NIR/MIR page](https://www.phovir.com/mieyra-nir-mir/) shows the device as it is
now. It has come a long way since I worked on it in its early days, when the first boards were
built and brought up. These pictures are PhovIR's.

{{ <embed src="https://www.phovir.com/wp-content/uploads/2026/09/Exploded-view_dark-background.webp" link="https://www.phovir.com/mieyra-nir-mir/" credit="PhovIR" width={1920} height={1080} alt="The MIEYRA unit taken apart on a dark background: an open black housing, four circuit boards stacked on brass standoffs with a gold sensor board at the front, and the closed housing with its lens." caption="The MIEYRA unit taken apart, as it is now." /> }}

{{ <embed src="https://www.phovir.com/wp-content/uploads/2026/10/phovir-understanding-the-invisible-world-home-hero-MIEYRA_.webp" link="https://www.phovir.com/" credit="PhovIR" width={1920} height={1080} alt="A blue PhovIR circuit board labelled MEMS module, with a gold sensor package in the middle and a fine-pitch connector at each side." caption="The MEMS module board, as it is now." /> }}

{{ <embed src="https://www.phovir.com/wp-content/uploads/2026/09/Cortica-Screen.png" link="https://www.phovir.com/investors/" credit="PhovIR" width={1672} height={941} alt="PhovIR's Cortica software: an interferogram plotted against mirror displacement at the top, the spectrum worked out from it below, with a list of captures on the right." caption="PhovIR's Cortica software, which came later: the interferogram above, the spectrum worked out from it below." /> }}

{{ <embed src="https://www.phovir.com/wp-content/uploads/2026/09/PhovIR-MIEYRA-vodka-spectral-.webp" link="https://www.phovir.com/validation/" credit="PhovIR" width={1920} height={527} alt="The black MIEYRA unit on a cable beside a shot glass, next to a chart of spectra for pure methanol, pure vodka and mixes of the two." caption="Spectra of methanol in vodka, measured with the unit." /> }}

{{ <embed src="https://www.phovir.com/wp-content/uploads/2026/09/polymer-mean_spectra_chart_NIR_ext.webp" link="https://www.phovir.com/validation/" credit="PhovIR" width={1920} height={572} alt="A chart of mean spectra for a set of plastics, next to a hand holding a white sample up to the MIEYRA unit." caption="Mean spectra of a set of plastics, measured with the unit." /> }}
