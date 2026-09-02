# PR Coder runbook — autonomous Codex finding responder

Durable operating guide for the `pr-coder` Hermes profile, which answers Codex
review findings on open PRs of this repo so they can be merged. This is not a
scratch tracker; keep it current when the mechanism changes.

**Owner:** Sean · **Runs:** webhook-triggered, plus an hourly safety net
**Last updated:** 2026-09-01

## Purpose

Codex posts P0–P5 findings on open PRs. `pr-coder` reads each finding, fixes it
on the PR branch in a dedicated clone, validates per `AGENTS.md` §10, pushes one
focused commit, and marks the finding handled. It never merges, never pushes to
`main`, and never force-pushes. Merging stays a human decision.

Conduct is governed by `AGENTS.md` (this repo) plus
`~/.hermes/profiles/pr-coder/SOUL.md`. Where `AGENTS.md` requires user approval,
the agent has no user: it stops and reports `needs-human`.

## The part that is not obvious

**Codex findings arrive on two different channels, and they close differently.**

| | Inline review thread | Review body |
|---|---|---|
| When | Cited line is inside the PR diff | Cited line is **outside** the diff, so Codex cannot anchor a comment |
| GraphQL | `pullRequest.reviewThreads` | `pullRequest.reviews` |
| Gate field | `findings` | `review_body_findings` |
| Has `isResolved`? | Yes | **No** |
| How the agent closes it | Reply to the thread, `resolveReviewThread`, read back `isResolved: true` | Add the **ROCKET** reaction to the review node, read back `viewerHasReacted: true` |

The review-body channel was invisible to this automation until 2026-09-01. A
finding on code the PR *affects* but does not *touch* lands there, so it is not
a rare edge case.

Because a review body has no resolvable thread, GitHub holds completion state as
a **reaction**. That keeps GitHub — not a local file — as the completion
authority: a crashed or half-finished run re-presents the review on the next
tick instead of silently dropping the finding.

**One reaction covers a whole review, and a review body may contain several
findings.** SOUL.md therefore requires the reaction only once *every* finding in
that review is fixed-and-pushed or reported `needs-human`. An extra tick is
cheap; a silently dropped P0 is not.

## Prerequisites

- [ ] Hermes profile `pr-coder` exists (`HERMES_HOME=~/.hermes/profiles/pr-coder`)
- [ ] Dedicated clone at `/Users/seandm/Projects/27vette-pr-agent` — never the live checkout at `~/Projects/27vette`
- [ ] `GITHUB_TOKEN` in `~/.hermes/profiles/pr-coder/.env` = classic PAT (`repo` scope) for the **`stingray-pr-agent`** machine account
- [ ] `stingray-pr-agent` is a collaborator on `seanzmc/27vette` with Write, invite accepted
- [ ] Repo-local git identity in the clone so commits are the bot's, not yours
- [ ] OpenRouter key for the model

Only the profile's own `.env` is loaded (`$HERMES_HOME/.env`). The root
`~/.hermes/.env` and other profiles' `.env` files are separate scopes and cannot
clobber this token.

## Configuration reference

| Thing | Value |
|---|---|
| Model | `z-ai/glm-5.3-flash` / `openrouter` (profile default) |
| Responder cron job | `2939d914f9ab`, every 1h, script `pr-review-gate.py`, delivers to `discord:1544037088368922716` |
| Watchdog cron job | `08830ae9547d`, every 20m, `no_agent`, script `pr-agent-watchdog.py` |
| Webhook route | `codex-pr-finding`, listener `*:8644`, script `pr-codex-trigger.py` |
| Public webhook URL | `https://pr-agent.stingraysales.net/webhooks/codex-pr-finding` |
| GitHub hook id | `672883313`, events `pull_request_review` + `pull_request_review_comment` |
| Done reaction | `ROCKET` (override with `PR_AGENT_DONE_REACTION`) |
| Watchdog thresholds | gate state stale > 90m; `NO_RUN_HOURS=4` |
| End-of-run notify | `scripts/pr-agent-notify.py` → macOS Notification Center (**not** Discord; Discord delivery comes from the cron job's `deliver`) |

The webhook is the primary trigger; the hourly cron is the recovery path for a
missed delivery, a failed run, or a push that did not close its finding. Both
call the same gate, which re-reads GitHub every time and trusts no cached state.

## Procedure — routine checks

### 1. Is the pipeline alive?

```
hermes -p pr-coder cron status
cat ~/.hermes/profiles/pr-coder/state/pr-agent-gate-state.json
```

**Expected:** gateway running, two jobs scheduled, `last_scan_at` within the
last ~65 minutes, `last_gate_error: null`.
**If it fails:** see Troubleshooting.

### 2. What does the gate actually see right now?

```
DRY_RUN=1 python3 ~/.hermes/profiles/pr-coder/scripts/pr-review-gate.py \
  | python3 -m json.tool
```

Live read, writes no state. `wakeAgent: false` means nothing actionable.
`skipped` counters say *why* things were passed over — `base_branch`,
`thread_resolved`, `thread_outdated`, `thread_non_codex_first`,
`review_done_reaction`. Read them before concluding the repo is clean.

### 3. Force a run

```
hermes -p pr-coder cron run 2939d914f9ab
```

Output lands in `~/.hermes/profiles/pr-coder/cron/output/2939d914f9ab/`.

### 4. Verify a run actually closed what it claims

Never take the run report's word for it. Re-run step 2: a genuinely closed
finding shows as `skipped.review_done_reaction: 1` (review body) or simply
disappears from `actionable_thread_ids` (inline thread). A claimed-but-unlanded
closure comes back as actionable — which is the design working, not a bug.

## Verification after any config change

- [ ] `gh api user --jq .login` with the profile token prints `stingray-pr-agent`
- [ ] `gh api repos/seanzmc/27vette --jq .permissions` shows `"push": true`
- [ ] Gateway `started_at` is **after** the `.env` mtime (otherwise the old token is still loaded)
- [ ] `git config --local --get-regexp 'user\.|credential\.'` in the clone shows the bot identity
- [ ] `gh api repos/seanzmc/27vette/hooks --jq '.[].last_response'` shows `200 active`

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Gate quiet, but an open Codex finding is visible on a PR | Finding is in a review body, not a thread — or the PR's base is not `main` | Run step 2 and read `skipped`. `base_branch > 0` means a stacked PR is being skipped by design |
| `Discord bot token already in use by the 'vette-coder' profile` | Two profiles sharing one bot token; whichever gateway starts first wins | `vette-coder` has `platforms.discord.enabled: false`. If it recurs, check that setting survived a config edit |
| Webhook delivers but nothing happens | Trigger script filtered the event | Check the gateway log for `[pr-codex-trigger] ignored event: reason=…`. `reason=author` on your own replies is correct loop-suppression, not a fault |
| `[pr-review-gate] WARNING: GITHUB_TOKEN was rejected` | Bot PAT expired, revoked, or wrong scope | Mint a new classic PAT on `stingray-pr-agent`, update `.env`, restart gateway. **Until then the done-reaction marker means the keyring identity, not the bot** |
| Findings silently marked done | A human added a ROCKET to a Codex review | Only the token identity's reaction counts. With the bot account in place, your reactions are inert — but do not react with ROCKET on Codex reviews out of habit |
| Watchdog cries "gate state stale" | Gateway was down, or the responder job is unscheduled | Confirm the gateway is running; the threshold is 90m against an hourly job |
| `gateway restart` seems to hang | A run is in flight; restart is deferred until it drains (force-drains at ~20m) | Let it finish. Check `logs/gateway.log` for `Restart deferred: waiting on N active work unit(s)` |
| Run takes 30+ minutes | Normal for a review-body finding, whose cited line is outside the diff and needs hunting | Watch turn count against `max_turns: 150`; a run past ~100 turns with no notify is worth reading |

## Rollback

Every change made on 2026-09-01 has a timestamped backup beside the original:

```
~/.hermes/profiles/pr-coder/config.yaml.bak.20260901_144058
~/.hermes/profiles/pr-coder/cron/jobs.json.bak.20260901_144058
~/.hermes/profiles/pr-coder/SOUL.md.bak.20260901_151500
~/.hermes/profiles/pr-coder/scripts/pr-review-gate.py.bak{,3,4}.*
~/.hermes/profiles/pr-coder/scripts/pr-codex-trigger.py.bak{,2}.*
~/.hermes/profiles/pr-coder/scripts/pr-agent-watchdog.py.bak.20260901_144058
~/.hermes/profiles/vette-coder/config.yaml.bak.20260901_144058
```

Restore the file, then `hermes -p pr-coder gateway restart`. To disable the
automation entirely without unpicking anything, pause both cron jobs and
deactivate GitHub hook `672883313`.

## Known gaps

- The full loop has never run end to end under the `stingray-pr-agent` identity. The next review-body finding is its first real exercise — watch that run.
- The classic PAT expires ~2026-12-01. Expiry now warns loudly in the gate output, but only if someone reads it; keep a calendar reminder.
- Cron job `2939d914f9ab` still carries a redundant `"model": "glm-5.3-flash"` override duplicating the profile default. Harmless; clear it next time that job is edited.
- The gate raises rather than paginates past 100 open PRs, 100 threads per PR, 50 reviews per PR, or 20 comments per thread. It fails loudly, which is correct, but it will need pagination eventually.
