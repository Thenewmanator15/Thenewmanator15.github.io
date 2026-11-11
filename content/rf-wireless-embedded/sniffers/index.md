+++
title = "Wireless packet sniffers"
description = "Two small boards that between them stream Wi-Fi, Bluetooth LE and 802.15.4 traffic into Wireshark."
[extra]
start = "2026-09"   # placeholder dates from the repos' first commits: Mathew to confirm
end = "now"
featured = true
milestone = true
role = false
panel = true
skills = ["ESP-IDF", "Zephyr", "Wireshark", "test strategy", "hardware-in-the-loop testing", "Python"]
text_only = true   # stock Seeed XIAO boards, nothing to photograph (Mathew, 1 Nov 2026)
my_part = "I wrote the firmware for both boards with AI coding agents helping. I also wrote the Python Wireshark plugin and the tools that test the boards."
result = "Both boards send one frame format, kept byte-identical to a Python reference. Hardware-in-the-loop tests caught defects that code review missed."
[[extra.readouts]]
label = "radios"
value = "3"
[[extra.readouts]]
label = "Wireshark interfaces"
value = "5"
[[extra.readouts]]
label = "802.15.4 timing"
value = "0.5 µs"
[[extra.readouts]]
label = "gaps in 150 retunes"
value = "0"
[[extra.matrix]]
title = "Thread, Zigbee and Matter"
sub = "802.15.4"
cols = ["ESP32-C6", "nRF54L15"]
rows = [
  ["Capture on channels 11 to 26", "yes", "yes"],
  ["Energy survey across the channels", "yes", "yes"],
  ["Networks named without a key: Thread or Zigbee, devices, sleepy devices", "yes", "yes"],
  ["Decryption of your own Thread or Zigbee traffic", "yes", "yes"],
  ["Corrupt frames counted", "no", "yes"],
  ["Timestamps", "about 0.5 µs, measured", "not yet measured"],
]
notes = ["The energy survey sees the Wi-Fi that overlaps most 802.15.4 channels, which a packet capture can't show. The timing was measured against the standard's fixed acknowledgement turnaround."]
[[extra.matrix]]
title = "Wi-Fi"
sub = "2.4 GHz"
cols = ["ESP32-C6", "nRF54L15"]
rows = [
  ["Capture at 2.4 GHz, 802.11b/g/n/ax", "yes", "-"],
  ["Channel hopping across 1, 6 and 11, or all of 1 to 13", "yes", "-"],
  ["Network survey: channel, signal, security", "yes", "-"],
  ["Wi-Fi 6 (802.11ax) decoding", "yes", "-"],
  ["Channel state information export", "yes", "-"],
]
notes = [
  "Wi-Fi is on the ESP32-C6 only. The nRF54L15 has no Wi-Fi radio.",
  "Wi-Fi is 2.4 GHz only. Encrypted payloads stay encrypted unless it's your own network and the capture caught a device joining. Wireshark can then decrypt them with the passphrase. The plugin flags each handshake it catches.",
]
[[extra.matrix]]
title = "Bluetooth LE"
sub = "advertising"
cols = ["ESP32-C6", "nRF54L15"]
rows = [
  ["Advertisements, periodic trains included", "yes", "yes"],
  ["Advertiser survey: stable and rotating addresses", "yes", "yes"],
  ["Your own devices followed through address changes, given their keys", "up to 5", "up to 8"],
  ["Decryption of your own Bluetooth Mesh traffic", "yes", "not yet tried"],
  ["Timestamps", "about ±20 µs, measured", "about −20 to +40 µs, measured on older firmware"],
]
notes = ["Both boards scan advertisements. Neither follows a connection."]
[[extra.tiles]]
value = "759"
label = "test functions in the laptop-side suite"
[[extra.tiles]]
value = "8"
label = "golden vectors, run on both boards"
[[extra.tiles]]
value = "51,200"
label = "random inputs in the robustness tests"
[[extra.tiles]]
value = "16"
label = "abuse checks against a live ESP32-C6"
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

## How a frame gets to Wireshark

On the ESP32-C6 each radio hands its frames to a task of its own. They share one ring buffer and one USB
link to the laptop, where a plugin hands them to Wireshark, one capture interface per radio.

{{ <chart name="sniffer-datapath" alt="Block diagram of the ESP32-C6 data path. On the board, each radio feeds its own queue into one 64 KB ring buffer. The 802.15.4 queue holds 32 frames, the Wi-Fi and Bluetooth LE queues 24 each. A send task passes it in 4 KB chunks over USB to a Python plugin on the laptop. The plugin gives Wireshark one capture interface per radio. The Wireshark toolbar's commands go back up to the board." caption="The ESP32-C6's data path, from its firmware. The dashed line is the toolbar's commands going back to the board." /> }}

{{ <chart name="sniffer-header" alt="Byte diagram of the 10-byte frame header: magic number 0x5AC6 in bytes 0 to 1, type in byte 2, flags in byte 3, sequence number in bytes 4 to 5, payload length up to 4096 in bytes 6 to 7, CRC-16 over bytes 0 to 7 in bytes 8 to 9. The payload follows." caption="The header every frame starts with, on both boards, from shared/frame.h." /> }}

## Measured

{{ <chart name="sniffer-link" alt="Bar chart of sustained link throughput: ESP32-C6 over USB 809.9 kB/s, nRF54L15 with DMA 94.3 kB/s, nRF54L15 polled 78.0 kB/s. A dashed line marks about 31 kB/s, what a full 802.15.4 channel produces." caption="Sustained throughput. The ESP32-C6 figure is the mean of 3 runs. The nRF54L15 goes through a UART bridge chip. A full 802.15.4 channel produces about 31 kB/s." /> }}

{{ <chart name="sniffer-sweep" alt="Line chart of ESP32-C6 throughput against payload size from 64 to 1500 bytes. Payload throughput rises from 680 kB/s at 64 bytes to between 774 and 781 kB/s from 512 bytes up. Bytes on the wire stay between 776 and 790 kB/s. The sweep counted the board's start-up time, so these read about 3% low." caption="Throughput by packet size on the ESP32-C6, 20 s per point. Solid: payload. Dashed: bytes on the wire, headers included. This first sweep counted the board's start-up time, so it reads about 3% under the corrected 809.9 kB/s." /> }}

{{ <chart name="sniffer-timing" alt="Log-scale chart from 0.1 µs to 10 ms. The ESP32-C6's 802.15.4 timestamp jitter is 0.5 µs, ranging from 0.4 to 0.9 µs across groups of frames. Dashed lines mark the radio's own timing: one symbol at 16 µs, the acknowledgement turnaround at 192 µs, a TSCH slot at 10 ms." caption="802.15.4 timestamp jitter on the ESP32-C6, the median standard deviation over 1,609 frames, against the radio's own timing. One chip, the shortest step in the radio signal, is 0.5 µs." /> }}

{{ <chart name="sniffer-ble-error" alt="Range chart of Bluetooth LE timestamp error, 1st to 99th percentile. ESP32-C6: −23 to +22 µs over 567 events. nRF54L15: −19 to +42 µs over 605 events, measured on older firmware." caption="Bluetooth LE timestamp error against a periodic advertising train, 1st to 99th percentile. The nRF54L15 was measured on older firmware." /> }}

{{ <chart name="sniffer-carrier" alt="Step chart of the ESP32-C6's energy reading on channel 20 while the nRF54L15 sent a test carrier: −105 dBm with the carrier off, −70 dBm with it on, −105 dBm once it is off again. The rise is 35 dB." caption="The ESP32-C6's energy survey seeing a carrier the nRF54L15 sent on channel 20, median reading." /> }}

{{ <chart name="sniffer-retune" alt="Diagram of the retune test: the capture switches between a busy channel and a quiet channel every 2 seconds. The first 40 seconds of 5 minutes are shown. Over 150 changes on each board there were 0 sequence gaps." caption="A sketch of how the retune test was run: a channel change every 2 s for 5 minutes. It gave 0 sequence gaps in 150 changes on each board." /> }}

## What each board supports

{{ <matrices /> }}

## Testing

{{ <tiles /> }}

{{ <chart name="sniffer-fuzz" alt="Bar chart on a log scale of random inputs per target. The HT and HE signal decoders get 20,000 each. Wi-Fi metadata, 802.15.4 metadata, access-point records and board replies get 2,000 each. CSI records get 2,200. Radiotap headers get 500, 802.15.4 tap records 300 and parser noise 200. That is 51,200 in all." caption="Random inputs per target in the laptop-side robustness tests. Each test uses a fixed seed, so every run is the same." /> }}

## More detail

<details class="fold"><summary><h2 id="why-i-built-it">Why I built it</h2></summary>

It started as a hobby. My Thread network at home wouldn't come up, so I built a sniffer to see
what the devices were actually sending. It now covers Wi-Fi and Bluetooth LE too.

</details>

<details class="fold"><summary><h2 id="how-it-works-with-wireshark">How it works with Wireshark</h2></summary>

Each board listens on its radio without joining the network. It wraps every frame in one shared format
and streams it down its USB cable to a Wireshark plugin on the laptop. On the nRF54L15 a bridge chip on
the board turns its serial link into USB. No network adapter or Npcap is needed.

The ESP32-C6 shows up in Wireshark as three capture interfaces: 802.15.4, Wi-Fi and Bluetooth LE. Picking
one picks the radio. The nRF54L15 adds two more of its own, 802.15.4 and Bluetooth LE. One plugin serves
both boards.

A toolbar inside Wireshark changes channel mid-capture with no restart. Across 150 channel changes on
each board, not one captured frame was lost. The toolbar also switches antenna. Its log window shows
frame counts. If anything is lost it shows the board's drop counters too. Each radio has its own
Wireshark profile, so the columns and filter buttons match what is being captured.

Captures save as pcapng. Each file records the board, radio, starting channel and drop counts, so a
capture shows months later whether anything was missed.

</details>

<details class="fold"><summary><h2 id="every-radio">Every radio</h2></summary>

| | ESP32-C6 | nRF54L15 |
|---|---|---|
| Channel change mid-capture, no restart (802.15.4, Wi-Fi) | yes | yes |
| Onboard or external antenna | yes | yes |
| Drop counters from the board | yes | ring overflows only |
| Link to the laptop | USB, about 810 kB/s | UART bridge, about 94 kB/s |

Decryption runs in Wireshark, from its own key tables. Capture never transmits: no acknowledgements, no
injection, no deauthentication. The one exception is opt-in. The ESP32-C6's Wi-Fi survey sends probe
requests if you ask for an active scan. The radios on a board share one front end, so each board
captures on one radio at a time.

</details>

<details class="fold"><summary><h2 id="how-it-was-tested">How it was tested</h2></summary>

The frame format has a Python reference. Both boards are tested against golden vectors from it.
Separate tests feed malformed input to the laptop-side decoders. An abuse script sends the ESP32-C6
garbage, command floods and 60 rapid retunes, then checks it is still capturing.

</details>
