+++
# Copy this folder to content/<channel slug>/<project id>/ and fill it in.
# The project id is the folder name: lower case letters, digits and hyphens only.
title = "Project title"
description = "What it is, in one line."
[extra]
start = "2026-01"          # YYYY-MM
end = "now"                # YYYY-MM or "now"
featured = false
milestone = false
role = false               # true for a job; then add bus_label = "Short name"
skills = ["Python"]        # 1 to 6, each one listed in data/skills.toml
text_only = false          # true: no photos, skills or key figures needed
hero = "hero.jpg"          # a photo in this folder, made with tools/prepare_images.py
hero_alt = "What the photo shows"
my_part = "What I did."
result = "What came of it."
[[extra.readouts]]         # 1 to 4; the first is the key figure
label = "label"
value = "value"
[[extra.proof]]            # at least one; kinds: code, data, document, photos, video, measurements, certificate
kind = "code"
label = "Code on GitHub"
url = "https://github.com/Thenewmanator15/"
# on_request = true        # instead of url, when the proof is only shown on request
# archive = "https://doi.org/..."   # optional permanent copy
+++

## Photos

{{ <figure src="hero.jpg" alt="What the photo shows" caption="One line about it." /> }}
