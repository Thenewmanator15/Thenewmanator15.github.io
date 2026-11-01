+++
title = "Wireless packet sniffers"
description = "Two small boards that between them stream Wi-Fi, Bluetooth LE and 802.15.4 traffic into Wireshark."
[extra]
start = "2026-09"   # placeholder dates from the repos' first commits: Mathew to confirm
end = "now"
featured = true
milestone = true
role = false
skills = ["ESP-IDF", "Zephyr", "Wireshark", "test strategy", "hardware-in-the-loop testing", "Python"]
text_only = true   # stock Seeed XIAO boards, nothing to photograph (Mathew, 1 Nov 2026)
my_part = "I wrote the firmware for both boards with AI coding agents helping. I also wrote the Python tools that check them."
result = "Both boards send one frame format, kept byte-identical to a Python reference. Hardware-in-the-loop tests caught defects that code review missed."
[[extra.readouts]]
label = "radios"
value = "3 protocols"
[[extra.readouts]]
label = "boards"
value = "2"
[[extra.readouts]]
label = "testing"
value = "hardware in the loop"
[[extra.proof]]
kind = "code"
label = "ESP32-C6 firmware and tests on GitHub"
url = "https://github.com/Thenewmanator15/esp32c6-sniffer"
[[extra.proof]]
kind = "code"
label = "nRF54L15 firmware on GitHub"
url = "https://github.com/Thenewmanator15/nrf54l15-sniffer"
[[extra.proof]]
kind = "measurements"
label = "Test logs"
on_request = true
+++

## Why I built it

It started as a hobby. My Thread network at home wouldn't come up, so I built a sniffer to see
what the devices were actually sending. It now covers Wi-Fi and Bluetooth LE too.

## How it works

In normal use each board listens on its radio without joining the network. It wraps every frame in one shared
format, then streams it over USB into Wireshark on a laptop.

## How it was tested

The frame format has a Python reference. Golden vectors from that reference run against both
boards, so a change on one side shows up at once. Malformed input and floods of traffic are part
of the same tests.
