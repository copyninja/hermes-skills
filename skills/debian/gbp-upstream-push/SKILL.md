---
title: gbp-upstream-push
description: "Re-push a diverged gbp upstream branch after import-orig."
name: gbp-upstream-push
version: 1.0.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: GPL-3.0
hermes:
  tags: [debian, gbp, git, upstream, force-push, package-maintenance]
  related_skills: [debci-api]
---

# gbp-upstream-push Skill

Re-push a diverged `upstream` branch after `gbp import-orig`, so the remote
upstream is in sync without losing upstream version history.

## When to Use

- You imported a new upstream version via `gbp import-orig` (or manually) and the
  local `upstream` branch has diverged from `origin/upstream`.
- `git push origin upstream` was rejected because the remote has commits you do
  not have locally (or vice versa).
- You need to choose force-push, rebase, or merge for the upstream branch.

## Prerequisites

- A Debian source tree with a gbp workflow.
- Local `upstream` branch and remote `origin/upstream`.
- The helper script `scripts/gbp-check-upstream.sh` for divergence diagnostics.

## How to Run

1. Diagnose the divergence with the helper script:
   `scripts/gbp-check-upstream.sh <pkg>`.
2. Identify which upstream versions are on each side (local vs remote).
3. Check what would be lost (reachability from `master`, upstream tags,
   pristine-tar, debian tags).
4. Choose the approach.
5. Push, then verify branch sync.

## Quick Reference

- Diagnose: `scripts/gbp-check-upstream.sh <pkg>`.
- Re-check divergence after each operation.
- Push other branches if needed (`master`, `pristine-tar`, `deploy/autopkgtest`).

## Procedure

1. Diagnose the divergence with `scripts/gbp-check-upstream.sh <pkg>`.
2. Identify upstream versions on each side.
3. Check what would be lost (reachability from `master`, upstream tags,
   pristine-tar, debian tags).
4. Choose the approach:
   - Clean `gbp import-orig` with older versions preserved on `master` + tagged +
     pristine-tar → **force push**.
   - Local upstream built on top of origin/upstream → **rebase** (abort on mass
     conflicts).
   - Preserve both histories and can resolve conflicts → **merge**.
5. Push other branches if needed.
6. Verify sync: `git rev-parse upstream` and `git rev-parse origin/upstream`.

## Pitfalls

- Do not rebase an upstream source tree across version gaps (mass content
  conflicts). Force push is the pragmatic solution for a clean import.
- Check whether older versions are on `master` + tagged + in pristine-tar before
  deciding — they are not lost if those three are intact.
- Check ALL branches after pushing upstream.
- Never force push without a backup (`cp -a`).
- Do not submit to debci for suites it does not accept.

## Verification

- `git rev-parse upstream` and `git rev-parse origin/upstream` match.
- `git log --oneline upstream..origin/upstream` shows only expected changes.
- Older upstream versions are preserved (tags, pristine-tar, master).
