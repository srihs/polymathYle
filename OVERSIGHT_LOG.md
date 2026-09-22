# Oversight log

Every oversight episode in this repository: a moment where a human corrected, rejected or
overrode something Claude produced. Each row matches one commit carrying `Oversight-`
git trailers, which hold the same information in the history itself.

**This file is research data** for a PhD on human oversight in agentic software
development. Rows are append-only: do not edit or delete existing rows, and do not
rewrite the commits they point to. The capture rules live in the "Oversight capture"
section of [CLAUDE.md](CLAUDE.md).

| Date | Commit | Type | What looked right but was not | What I did | Durable |
| --- | --- | --- | --- | --- | --- |
| 2026-09-22 | e31945a | data-model | I modelled the fixed level list as exactly the CEFR bands the user listed, leaving no place for Polymath's own pre-junior level below Pre A1. | Caught the missing level and told me to add Pre-Junior as a non-CEFR level standing before Pre A1. | no |
