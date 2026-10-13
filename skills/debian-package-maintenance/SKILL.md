---
name: debian-package-maintenance
description: "Pull Debian source repos and query BTS/QA for RC bugs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [debian, package, bts, qa, git, salsa]
    category: software-development
---

# Debian Package Maintenance

## When to Use

Pull latest changes, investigate RC bugs, prepare uploads, or any package maintenance task for a Debian source package. Covers the local repository layout, Salsa Git access, and Debian BTS/QA tooling.

## Routing

| Task | Read first |
|---|---|
| Pull latest + report RC bugs (the common "let's work on the RC bug" start) | This file (below) |
| Query BTS by severity/tag, filter outstanding vs resolved | `references/bts-query.md` |
| Read QA developer page columns: RC count, buildd state, FTBFS, experimental | `references/qa-page-readout.md` |
| Build, sign, upload, and verify build status | `references/build-verify.md` |
| Plan and add autopkgtest to a package | `references/autopkgtest-planning.md` |

## Local repository layout

- Debian source package git clones live under `~/Documents/Debian/<dirname>/`.
- **The directory name is the source package name, which may differ from the binary package name the user mentions.** `bpfcc-tools` (binary) → `bpfcc/` (source dir). When in doubt, list `~/Documents/Debian/` and match by source package name.
- Some source packages carry a `.` in the dir name (e.g. `python3-foo`). Match on source package name, not binary.

## Pull latest changes

```bash
cd ~/Documents/Debian/<dirname>
git status          # confirm branch + clean tree
git remote -v       # confirm salsa.debian.org origin
git pull origin master   # or the relevant branch
```

- SSH to `git@salsa.debian.org` must work. If `git pull` fails with `agent refused operation` but `ssh -T git@salsa.debian.org` succeeds, the SSH agent socket is not reachable from the git invocation's environment — use the working `ssh` to confirm the key is valid, then re-run `git pull` (the socket typically becomes visible on retry without env acrobatics).
- Do NOT export `SSH_AUTH_SOCK` from nested command substitution — that pattern triggers security scanners and is unnecessary; a plain retry usually works.

## Import a new upstream version with gbp

When the user asks to upgrade to a new upstream release:

### 1. Get the orig tarball

Download or locate the `+ds` orig tarball (e.g. `bpfcc_0.37.0+ds.orig.tar.xz`) in the parent directory of the repo (e.g. `~/Documents/Debian/bpfcc_0.37.0+ds.orig.tar.xz`).

### 2. Set Debian changelog identity

gbp's postimport hook runs `dch` which requires `DEBEMAIL` (and optionally `DEBNAME`). Set them from the git config if not already in the environment:

```bash
DEBEMAIL=$(git config user.email) DEBNAME=$(git config user.name) \
  gbp import-orig --pristine-tar --upstream-version=<version> ../<pkg>_<version>.orig.tar.xz
```

- Omit `--upstream-version` only when gbp can auto-detect it from the tarball filename; when in doubt, pass it explicitly.
- `--pristine-tar` keeps a pristine-tar branch for rebuilds — include it unless told otherwise.

### 3. Handle the pre-import commit requirement

gbp refuses to import when the working tree has uncommitted changes. After a `git pull`, the newly fetched upstream files are often staged but not committed. Commit them first:

```bash
git commit -m "Import upstream <version> source"
```

Then run the `gbp import-orig` command above.

### 4. Commit the result

gbp creates a new changelog entry and commits on master. Verify with `git log --oneline -3` and check `debian/changelog` head for the new version.

## Refresh quilt patches against new upstream

After importing a new upstream version, the existing Debian patches may fail to apply because upstream changed the files they target. The standard workflow:

### 1. Check patch applicability

```bash
quilt push -a
```

- If all patches apply: done. Proceed to build/test.
- If a patch fails: quilt stops at the first failure. The remaining patches are not tried. Note which patch failed and why.

### 2. Read the DEP-3 header before touching a patch

Every patch in `debian/patches/` should carry a DEP-3 header:

```
Description: <one-line summary>
Author: <name>
Forwarded: <not-needed | yes | no | pending | https://...>
```

Read the `Description:` before deciding whether to drop, refresh, or rewrite a patch. The description tells you what the patch is *for* — that intent may still be valid even when the exact hunks no longer apply. Do not drop a patch simply because it failed to apply; check what it was trying to accomplish first.

### 3. Diagnose a failed patch

When `quilt push` fails on a patch:

1. **Read the `.rej` file** (if created) to see what hunks failed and where.
2. **Read the patch itself** — particularly the `Description:` and the context lines — to understand what file and region it targets.
3. **Compare the current upstream file** against the patch's expected context. Upstream may have:
   - Rewritten the function/section the patch touches
   - Renamed variables, restructured conditionals, or moved code
   - Added new variables or build logic that changed line numbers
4. **Check whether the patch's goal is already upstream.** Sometimes upstream absorbs the same fix. If the upstream file now does what the patch wanted, the patch can be dropped (remove from `debian/patches/series`).

### 4. Refresh or rewrite the patch

- If the patch's goal is still needed but the context changed: rewrite the hunks against the current upstream file, keeping the same DEP-3 header and `Description:`.
- If the patch's goal is now upstream: remove it from `debian/patches/series` (and delete the file).
- If the patch is forwarded from upstream and the upstream version already includes it: remove from `series`.

### 5. Continue pushing remaining patches

After fixing the failed patch, push the rest:

```bash
quilt push -a
```

Repeat diagnosis/refresh for any further failures.

### 6. Verify the full tree

After all patches apply:

```bash
git diff   # review the accumulated patch state
git log --oneline -3   # confirm the import commit is in place
```

## Identify RC bugs

1. **BTS source package bug list:** `https://bugs.debian.org/cgi-bin/pkgreport.cgi?src=<source-package>` — scan for severity=important/grave/critical (RC).
2. **QA developer page:** `https://qa.debian.org/developer.php?login=<logname>&comaint=yes` — RC count, buildd status, FTBFS state, experimental status in one view.
3. **Tracker:** `https://tracker.debian.org/pkg/<package>` — release-critical status and version tracking.
4. **Individual bug:** `https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=<number>` — full report, tags, forward status.

Filter RC bugs to: severity critical/grave/serious AND status not done/resolved.

## Import a new upstream version with gbp --uscan

When the upstream tarball is not yet downloaded locally, `gbp import-orig --uscan` can fetch it automatically from the `watch` file:

```bash
cd ~/Documents/Debian/<dirname>
DEBEMAIL=$(git config user.email) DEBNAME=$(git config user.name) \
  gbp import-orig --pristine-tar --uscan
```

- `--uscan` reads `debian/watch` and downloads the latest upstream tarball matching the watch pattern.
- Use this when the tarball is not already on disk; prefer the explicit `../<pkg>_<version>.orig.tar.xz` form (documented above) when the tarball is already present — it avoids an unnecessary network fetch and makes the version explicit.
- The same `--pristine-tar`, `DEBEMAIL`/`DEBNAME`, and pre-import commit requirements apply as in the explicit tarball form.


## Report back

After pull + RC bug check, report:
- Repo path, branch, clean/dirty state
- Current version (from `debian/changelog` head)
- Latest commit summary
- RC bug count and the bug numbers with one-line titles
- Notable: experimental build status, FTBFS, upstream newer version available, forward status of RC bugs

Keep it tabular or bulleted — no narrative filler.

## Pitfalls

- **Binary vs source package name mismatch.** User says "bpfcc-tools" but the git dir is `bpfcc/`. Always resolve to the source package name before searching the filesystem or querying BTS.
- **RC bug filed against a binary package, not source.** A bug tagged `[bpfcc-tools]` lives under the `bpfcc` source package BTS page. Query by source package, not binary.
- **Experimental failures are not necessarily the RC bug.** bpfcc experimental builds fail across all arches — that is a separate build environment issue, not necessarily related to the RC bug. Check both but keep them distinct.
- **NMU version suffix.** `0.35.0+ds-1.1` — the `.1` indicates a non-maintainer upload. The changelog names the NMUer. Don't assume the maintainer made the latest commit.
- **Searching for the binary package name as a directory fails.** `find /home/vasudev -name "bpfcc-tools" -type d` returns nothing. Search by source package dir name or list the parent dir.
- **Do NOT tag before upload is accepted.** A premature tag diverges from the archive state; wait for the tracker news entry confirming acceptance before running `gbp buildpackage --git-tag-only`.
- **The BTS bug title is not always the actual failure.** Read the build log before concluding which bug is responsible. A "GCC-16 FTBFS" bug may turn out to be a LuaJIT assertion on a specific arch — check the toolchain version in the log and where the build actually stops before attributing the cause.
- **getbuildlog can fail silently with an explicit version.** If `getbuildlog pkg ver arch` returns an error, retry with `getbuildlog pkg last arch` — the explicit version string may not match what buildd stored.
- **Needs-Build is not a failure.** An arch sitting in Needs-Build means no buildd has picked it up yet — not that it failed. Distinguish from Build-Attempted (failure) and Installed (success).
- **Clean build artifacts before building source package.** Remove `.pc/`, extracted source directories, and any `.dsc`/`.tar.xz`/`.buildinfo`/`.changes` files from the repo root before running `dpkg-buildpackage -S`. Stale artifacts cause dpkg-source to see unexpected changes and fail.
- **Upstream source symlinks break dpkg-source.** If the orig tarball contains symlinks (e.g., `libbpf-tools/arm64/vmlinux.h -> vmlinux_614.h`, `tools/cobjnew_example.txt -> lib/uobjnew_example.txt`), `dpkg-source -b` will error with "cannot represent changes" because it cannot represent symlink creation in the Debian diff. The source tree must match the unpacked orig tarball exactly — do not add or modify symlinks outside of patches.
- **Convert upstream git diffs to Debian patch format correctly.** Strip `diff --git`, `index`, and extra `--- a/`/`+++ b/` lines; keep only the `--- a/file` and `+++ b/file` headers and unified hunks. Add DEP-3 header (Description, Author, Forwarded). Filter to only files that exist in the current source tree — upstream PRs may touch files not present in this version. Use a script for reliable conversion; manual editing is error-prone.

## References

- `references/bts-query.md` — BTS query URL patterns and severity/tag filtering
- `references/qa-page-readout.md` — how to read the QA developer page columns