---
description: Capture the correction I just made as an oversight episode (commit with trailers + log row)
---

The user has just caught something wrong in your work. Capture it as an oversight episode,
following the "Oversight capture" section of CLAUDE.md.

Anything the user typed after the command is context for the episode: $ARGUMENTS

Work through these steps in order.

**1. Collect the four trailer values.** Take whatever the user already gave you in
`$ARGUMENTS` and in the conversation. Ask for the rest in a single `AskUserQuestion` call,
one question per missing value, with your best guess as the first option:

- `Oversight-Type` — one of: architecture, business-rule, correctness, security, scope,
  data-model, performance, dependency.
- `Oversight-Trigger` — what you produced that looked correct and was not, one sentence.
- `Oversight-Action` — what the user did about it, one sentence.
- `Oversight-Durable` — `yes` if this produced a new or changed rule in CLAUDE.md, a
  subagent definition, a test, or a lint rule; `no` otherwise.

Never invent a value. If you cannot tell whether something even counts as an episode, ask
before committing: a false entry is worse than a missing one.

**2. Show what will be committed.** Run `git status --short` and `git diff --stat`. If the
working tree also holds unrelated feature work, tell the user which paths look unrelated
and ask whether to commit only the correction's paths. The episode must be its own commit.

**3. Stage the change.** `git add` the paths that belong to this correction (or `git add -A`
when everything in the tree is part of it). Never stage `.env`, `credentials.json` or any
other secret.

**4. Commit.** One short subject line describing the correction, then a blank line, then
the four trailers exactly as named, then the attribution line the session requires:

    Fix <what the correction was>

    Oversight-Type: <type>
    Oversight-Trigger: <trigger>
    Oversight-Action: <action>
    Oversight-Durable: <yes|no>

    Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>

Write it with a heredoc (`git commit -F -`) so the blank lines and trailers survive. Do not
amend, squash or rebase: this commit is part of the dataset.

**5. Append the log row.** Add one row to the end of the table in `OVERSIGHT_LOG.md`, using
the short SHA from `git rev-parse --short HEAD` and today's date in `YYYY-MM-DD`:

    | 2026-09-21 | abc1234 | correctness | <trigger> | <action> | yes |

Escape any `|` in the text as `\|` so the table stays valid. Leave existing rows untouched.
Commit that row too, with a subject such as `Log oversight episode abc1234` and no
`Oversight-` trailers, since the log row is bookkeeping rather than a new episode.

**6. Print the result.** Show the user the episode commit's full SHA
(`git rev-parse HEAD`), its subject, and the row you appended, so they can see it worked.
Do not push unless the user asks.
