# Transcribed tables — the part that must not be improvised

Each CSV carries a header block of `#` comment lines naming the document, version,
section and page it was transcribed from, plus `# verified: true|false`.

`scripts/build_rulebase.py` turns these into `.lp` fact files and **refuses to run** on a
malformed row or a missing header field. Any table with `verified: false` adds a warning
to every determination that reads it, and the verdict UI shows an UNVERIFIED banner.

Do not edit the generated `.lp` files. Edit the CSV, regenerate, re-run the golden tests.
