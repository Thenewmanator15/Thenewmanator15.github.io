+++
title = "Colour themes for PDF"
description = "One PDF that carries its author's own light, dark or higher-contrast themes."
[extra]
start = "2026-10"   # placeholder from the repo's first commit: Mathew to confirm
end = "now"
featured = false
milestone = false
role = false
skills = ["PDF", "accessibility", "open standards", "Typst"]
text_only = false
my_part = "I built the proof of concept for a proposal to the PDF Association, with a live demo."
result = "Readers with a dark mode invert the page or swap its colours, which spoils charts. With themes, readers that support them swap a small palette. Others show the page exactly as now."
[[extra.readouts]]
label = "themes"
value = "light · dark · higher contrast"
[[extra.proof]]
kind = "code"
label = "Code on GitHub"
url = "https://github.com/Thenewmanator15/pdf-themes"
[[extra.proof]]
kind = "document"
label = "Live demo"
url = "https://thenewmanator15.github.io/pdf-themes/"
+++

## Why I built it

PDF readers that offer a dark mode make it up themselves. They invert the page or swap its
colours, which spoils charts. Readers who need more contrast or a tinted background get the same
treatment. The file has no way to say how it should look in the dark, so I built one. My own CV is a tagged, accessible PDF, so this felt like the next step.
