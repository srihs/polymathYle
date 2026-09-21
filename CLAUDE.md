# Polymath YLE

Django LMS for Polymath School of English.

## Oversight capture

This repository is research data for a PhD on human oversight in agentic software
development. The rules below are addressed to Claude and must be followed.

- When the user corrects you, rejects your approach, overrides a decision, or tells you
  that something you produced is wrong, treat that as an **OVERSIGHT EPISODE**.
- Commit that correction **on its own**, separately from feature work, as soon as it is
  resolved. Do not fold it into a larger commit.
- The commit message must end with these git trailers, after a blank line:

      Oversight-Type: <one of: architecture, business-rule, correctness, security, scope,
                       data-model, performance, dependency>
      Oversight-Trigger: <what you produced that looked correct and was not, one sentence>
      Oversight-Action: <what the user did about it, one sentence>
      Oversight-Durable: <yes if this produced a new or changed rule in CLAUDE.md, a
                          subagent definition, a test, or a lint rule; no otherwise>

- Never squash, amend, rebase or force-push a commit carrying an `Oversight-` trailer.
  That history is the dataset.
- Never delete or overwrite a subagent definition or a CLAUDE.md section. Change it and
  commit the change, so the evolution stays visible.
- After writing such a commit, append the matching row to `OVERSIGHT_LOG.md`.
- If you are unsure whether something counts as an episode, ask the user rather than
  guessing. A false entry is worse than a missing one.

The `/oversight` slash command (`.claude/commands/oversight.md`) performs this capture.
