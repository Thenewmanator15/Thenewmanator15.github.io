+++
title = "Electronics and embedded engineer, PhovIR"
description = "Firmware and electronics for a handheld spectrometer at a start-up."
[extra]
still_to_come = ["write-up"]
start = "2025-10"
end = "2025-12"
featured = false
milestone = true
role = true
bus_label = "PhovIR"
text_only = true
skills = ["ESP32", "embedded firmware", "EMI and grounding"]
my_part = "I wrote the ESP32 firmware and device drivers, including control of the high-voltage MEMS drive. I led the engineering review of the board layout, then assembled and brought up the boards with the team."
[[extra.proof]]
kind = "document"
label = "Details on request"
on_request = true
+++

## The company

[PhovIR](https://phovir.com/) is a University of Manchester spin-out making a handheld, MEMS-based
infrared (FTIR) spectrometer
([PhovIR on LinkedIn](https://www.linkedin.com/company/phovir-technologies/)). I joined on a
three-month contract to set up the embedded and electronics side, taking the device from an
early concept towards a consumer-ready prototype.

## How we got there

I started with the firmware on the ESP32. I wrote drivers for the ADCs and DACs. I also wrote
the control for the high-voltage MEMS drive. I made the firmware interrupt-driven to keep the
latency down between driving the MEMS and reading the photodiode. I kept the hardware layer separate so
MQTT or a web interface could sit on top later.

While the first boards were being laid out, I led the engineering review. Where parts went was
guided by what I knew about heat, coupling and leakage at the photodiode. I designed for EMC
and for production.

When the boards arrived, I assembled them with the team and brought them up, the MEMS drive
included. I then fault-found at board and system level. The results went into the next revision.
