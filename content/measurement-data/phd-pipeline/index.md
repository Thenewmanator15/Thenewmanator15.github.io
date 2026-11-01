+++
title = "PhD data pipeline"
description = "The analysis behind my PhD, rebuilt in Julia: from about 4 TB of compressed captures to decoded spectra, with every number traced to its code."
[extra]
start = "2024-01"   # the Julia package; on and off until the 2026 rebuild (Mathew, 1 Nov 2026)
end = "now"
featured = false
milestone = false
role = false
skills = ["Julia", "CUDA", "Python", "Rust", "signal processing", "CI"]
text_only = false
my_part = "I rebuilt the analysis as Julia packages that run from the raw captures to the decoded spectra, with a thesis build that traces every number to its code. I built it with AI coding agents, directing the design and checking the results."
result = "Profiling showed reading the compressed captures ran on one thread, at 0.3 to 0.5 GB/s. A parallel reader in a prototype reached 9.8 GB/s for the decoding alone, about 24 times faster."
[[extra.readouts]]
label = "reading"
value = "~24× faster"
[[extra.readouts]]
label = "captures"
value = "~4 TB"
[[extra.readouts]]
label = "decode"
value = "17 µs"
[[extra.proof]]
kind = "code"
label = "Code"
on_request = true
+++

## Why it mattered

In 2022 the first coded data looked flat, as if the experiment hadn't worked.

Rebuilding the analysis is what found the answer. The gate's pattern repeated slightly sooner
than the capture expected, so it drifted out of step with the data. The likeliest cause is samples
lost in the capture. Folded at the right period, the same data gave the
[PhD's main result](/instruments/phd/): the same signal-to-noise about 30 times faster, at the cost
of a higher dose.

A pipeline that traces every number to its code is what makes that result checkable by someone
else.

## The data

Each capture is 4 s of the detector, sampled at 1 GS/s with 16 bits: about 8 GB raw. Blosc
compression with zstd stores it at about half that. The August to September 2022 campaign ran 87 experiments
in 17 days. Its gate runs alone left 958 files, 3.95 TB compressed.

## The pipeline

1. Read. One package reads every format the lab produced (HDF5, TDMS, LeCroy, Keysight and
   MATLAB files) behind a single interface. It reads ahead on its own task.
2. Remove the converter pattern. The ADC interleaves four converters with slightly different
   offsets, which leaves a pattern repeating every four samples. Subtracting each converter's
   median removes it.
3. Select captures. Each capture is screened on its ion rate and on a statistical test
   against the same data folded at a wrong period.
4. Find the ions. A threshold at eight standard deviations, with crossings closer than
   50 samples merged. A matched filter was tested against it and gained nothing.
5. Fold. Events fold at the period measured from the data, not the one commanded, because
   the gate repeated 2,297 ppm early ([the timing problem](/instruments/phd/timing-problem/)).
6. Combine. The folds sum without weights, which the thesis shows is the maximum-likelihood
   estimate.
7. Decode. Six decodes, from the fast m-sequence transform to Richardson–Lucy, compared on
   the same data ([decoding the signal](/instruments/phd/decoding/)).
8. Figures. Python draws every figure from reduced tables.

## Speeds

All measured on an i7-12700K with an RTX 5070 Ti, in September and October 2026.

| Step | Before | After |
|---|---|---|
| Reading compressed captures | 0.32–0.46 GB/s, one thread | 9.8 GB/s decoding on 20 tasks, 8.7 GB/s with the read (prototype) |
| Reading one capture, as shipped | 21–29 s | 6.0 s |
| Finding events, per frame | 71 ms | 23–29 ms on the GPU |
| Fitting pulses | 15,600 windows/s | 64,900 windows/s on the GPU |
| Searching for the period | | 12.6× faster, 3,600× less memory |
| Folding | | 6× faster on 8 threads |

The decode itself is fast. At order 13, 8,191 symbols, the in-place fast m-sequence transform
takes 17 µs. That's 499 times faster than the direct matrix method. Against an FFT route it is about
17 times faster at this order. Across orders 10 to 16 the gain runs from 4 to 22 times.

## The architecture

- HtTofSims.jl, the processing package: the transform, event finding, folding, period
  search, Wiener decoding, the converter-pattern fix and pulse fitting. It also models the
  converter card. A simulator of the beam's ions lets every step be tested on data with a known
  answer.
- GPU kernels written with KernelAbstractions.jl, so they aren't tied to one vendor. They
  run on CUDA here. A hand-written CUDA kernel undoes Blosc's bitshuffle, in a GPU decode
  prototype.
- InstrumentFiles.jl, the readers, tested in CI.
- A Rust decoder for the compact pulse-record format.
- The thesis build. pytask drives 33 figure folders. About 445 numbers in the text come from
  21 values files. Each file carries the hashes of the inputs that made it. A replication check re-ran a nine-script chain and got all 46 outputs back identical.

The heavy reductions from raw captures run in Julia as their own step. The build then redraws
every figure from their tables.

## How it got here

During the PhD the analysis was in MATLAB, then Julia. In 2024 it moved into a Julia package,
which I worked on and off. In September and October 2026 I rebuilt it as it stands now. I've also designed an FPGA core
that would timestamp the gate and each ion on the capture card, for the host to fold. It runs in
simulation only, so far.
