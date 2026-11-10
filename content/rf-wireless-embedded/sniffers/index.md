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
my_part = "I wrote the firmware for both boards with AI coding agents helping. I also wrote the Python Wireshark plugin and the tools that test the boards."
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

## How it works with Wireshark

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

## What each board supports

### Thread, Zigbee and Matter (802.15.4)

| | ESP32-C6 | nRF54L15 |
|---|---|---|
| Capture on channels 11 to 26 | yes | yes |
| Energy survey across the channels | yes | yes |
| Networks named without a key: Thread or Zigbee, devices, sleepy devices | yes | yes |
| Decryption of your own Thread or Zigbee traffic | yes | yes |
| Corrupt frames counted | no | yes |
| Timestamps | about 0.5 µs, measured | not yet measured |

The energy survey sees the Wi-Fi that overlaps most 802.15.4 channels, which a packet capture can't
show. The timing was measured against the standard's fixed acknowledgement turnaround.

### Wi-Fi

Wi-Fi is on the ESP32-C6 only. The nRF54L15 has no Wi-Fi radio.

| | ESP32-C6 |
|---|---|
| Capture at 2.4 GHz, 802.11b/g/n/ax | yes |
| Channel hopping across 1, 6 and 11, or all of 1 to 13 | yes |
| Network survey: channel, signal, security | yes |
| Wi-Fi 6 (802.11ax) decoding | yes |
| Channel state information export | yes |

Wi-Fi is 2.4 GHz only. Encrypted payloads stay encrypted unless it's your own network and the capture
caught a device joining. Wireshark can then decrypt them with the passphrase. The plugin flags each
handshake it catches.

### Bluetooth LE

| | ESP32-C6 | nRF54L15 |
|---|---|---|
| Advertisements, periodic trains included | yes | yes |
| Advertiser survey: stable and rotating addresses | yes | yes |
| Your own devices followed through address changes, given their keys | up to 5 | up to 8 |
| Decryption of your own Bluetooth Mesh traffic | yes | not yet tried |
| Timestamps | about ±20 µs, measured | about −20 to +40 µs, measured on older firmware |

Both boards scan advertisements. Neither follows a connection.

### Every radio

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

## How it was tested

The frame format has a Python reference. Both boards are tested against golden vectors from it.
Separate tests feed malformed input to the laptop-side decoders. An abuse script sends the ESP32-C6
garbage, command floods and 60 rapid retunes, then checks it is still capturing.
