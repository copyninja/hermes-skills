---
title: gbp-upstream-push
description: "Re-push diverged gbp upstream after import-orig."
name: gbp-upstream-push
version: 1.0.0
author: Vasudev Kamath
license: GPL-3.0
hermes:
  tags: [debian, gbp, git, upstream, force-push, package-maintenance]
  related_skills: [debci-api]
---

## When to Use

Use this skill when you have:
- Imported a new upstream version via `gbp import-orig` (or manually) and the local `upstream` branch has diverged from `origin/upstream`.
- Tried `git push origin upstream` and it was rejected because the remote has commits you don't have locally (or vice versa).
- Tried rebase and gotten mass conflicts on upstream source files.

The goal: get the `upstream` branch pushed to origin in a way that does not lose upstream version history, does not break build systems, and does not require manual conflict resolution.

## Decision Process

### Step 1: Diagnose the divergence

```bash
# Check the divergence
git log --oneline upstream..origin/upstream   # commits on remote not in local
git log --oneline origin/upstream..upstream   # commits on local not in remote
git merge-base upstream origin/upstream       # common ancestor
git rev-list --count upstream                 # local upstream commit count
git rev-list --count origin/upstream          # remote upstream commit count
```

### Step 2: Identify what upstream versions are on each side

```bash
# All upstream version commits on local
git log --oneline upstream | grep "New upstream version"

# All upstream version commits on remote
git log --oneline origin/upstream | grep "New upstream version"
```

### Step 3: Check what would be lost

For each commit present on `origin/upstream` but NOT on local `upstream`:

```bash
# Is the commit reachable from master?
git merge-base --is-ancestor <commit> master && echo "preserved on master" || echo "NOT on master"

# Is there an upstream tag for this version?
git tag -l "upstream/<version>"

# Is pristine-tar data available?
git log --oneline pristine-tar | grep "<version>"

# Is there a debian version tag?
git tag -l "debian/<version>*"
```

### Step 4: Choose the approach

| Situation | Action |
|---|---|
| Local upstream is a clean `gbp import-orig` (fresh import of new tarball) and all older upstream versions are preserved on `master` + tagged + in `pristine-tar` | **Force push** — `git push --force origin upstream` |
| Local upstream was built on top of origin/upstream and should replay its commits | **Rebase** — but only if upstream source files don't conflict. If mass conflicts appear (README, changelog, dozens of source files), abort — rebase is wrong for upstream source trees across major version jumps |
| You want to preserve both histories and can resolve conflicts | **Merge** — `git merge origin/upstream` then push, but expect heavy conflicts on upstream source files |

**Default: force push** when local upstream is a clean gbp import. Older versions are NOT lost — they live on in `master` history, `upstream/VERSION` tags, and `pristine-tar` branch.

### Step 5: Force push (if chosen)

```bash
# Verify what will change
git log --oneline origin/upstream..upstream       # what local adds
git log --oneline upstream..origin/upstream       # what remote loses

# Push
git push --force origin upstream

# Verify
git rev-parse upstream
git rev-parse origin/upstream
# Both should match
```

### Step 6: Push other branches if needed

```bash
# Check all branches for out-of-sync state
for branch in master pristine-tar deploy/autopkgtest; do
    LOCAL=$(git rev-parse $branch)
    REMOTE=$(git rev-parse origin/$branch 2>/dev/null || echo none)
    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "$branch needs push"
    fi
done
```

## What Build Systems Actually Need

Debian build infrastructure (gbp buildd, openqa, salsa CI) does **NOT** walk the `upstream` branch history. They use:

1. **Upstream tags** (`upstream/VERSION`) — every upstream version should have one
2. **pristine-tar branch** — stores orig.tar reconstruction data per version
3. **debian branch** (`master` or `debian/master`) — has the full packaging history

The `upstream` branch is primarily a convenience reference for `gbp` commands. Losing older versions from this branch does not break builds as long as #1–#3 are intact.

## Backup First

Before any force push:

```bash
cp -a /path/to/repo /path/to/repo-backup-$(date +%Y%m%d-%H%M)
```

Or use git's reflog as a safety net:
```bash
# reflog is kept for 90 days by default
git reflog show upstream
```

## Pitfalls

- **Do not rebase an upstream source tree across version gaps.** When rebasing `gbp import-orig` output (new version N) onto an older upstream branch (version N-2, N-3), every file that changed between those upstream releases produces a content conflict. The rebase is not wrong conceptually — the tree-level diffs are just too large. Force push is the pragmatic solution when you have a clean import.
- **Do not assume `git push --force` loses upstream versions.** Check whether older versions are on `master`, tagged, and in `pristine-tar` BEFORE deciding. The upstream branch is the least-important of the three preservation mechanisms.
- **Check ALL branches after pushing upstream.** The `upstream` branch is often not the only one out of sync — `master`, `pristine-tar`, and deployment branches may also need pushing. Check each one.
- **Never force push without a backup.** `cp -a` takes seconds and gives you a restore point if something goes wrong.
- **Do not submit to debci for suites it does not accept.** See `debci-api` — this debci instance only accepts `unstable`. Submitting to `experimental` or other suites wastes debci slots and produces no result.

## Quick Reference

```bash
# Full diagnostic one-liner
git log --oneline upstream..origin/upstream; echo "---"; git log --oneline origin/upstream..upstream; echo "---"; git merge-base upstream origin/upstream

# Check preservation of a specific upstream version
VER=0.35.0+ds
COMMIT=$(git log --oneline origin/upstream | grep "New upstream version.*$VER" | head -1 | cut -d' ' -f1)
echo "On master: $(git merge-base --is-ancestor $COMMIT master && echo YES || echo NO)"
echo "Tagged: $(git rev-parse upstream/$VER 2>/dev/null && echo YES || echo NO)"
echo "In pristine-tar: $(git log --oneline pristine-tar | grep -c "$VER" 2>/dev/null || echo 0)"
```
