# Build, Sign, Upload, and Verify

## When to Use

The full Debian package build → sign → upload → monitor lifecycle, from the local git working copy through to buildd.debian.org status tracking. Use when the user asks to build/upload a package, or when verifying whether an upload reached unstable and built successfully.

## Prerequisites (verify once before starting)

- GPG signing key available: `gpg --list-keys --keyid-format long` should show the Debian upload key with ultimate trust.
- `~/.dput.cf` or `/etc/dput.cf` has an `[ftp-master]` stanza pointing at `ftp.upload.debian.org`.
- `gbp`, `sbuild`, `debsign`, `dput`, `getbuildlog` (from `devscripts`) are installed.
- Working copy is under `~/Documents/Debian/<source-pkg-dir>/`.

## Standard build + upload workflow

### 1. Confirm repo state

```bash
cd ~/Documents/Debian/<dirname>
git status          # clean tree, on master
git log --oneline -3   # confirm upstream import is in
git diff debian/changelog   # any unstaged changelog edits?
```

- If the changelog has local unstaged edits (e.g. a version entry written but not committed), decide whether to commit or discard before building.
- `git status` showing "ahead of origin/master by N commits" means local commits are not yet pushed — normal before an upload.

### 2. Build the source package with sbuild

```bash
gbp buildpackage --git-builder=sbuild -s --source-only-changes -d unstable --git-ignore-new
```

- `-s` = build source package (mandatory for uploads).
- `--source-only-changes` = only source changes, no binary rebuild of already-built binaries.
- `--git-ignore-new` = proceed even if the tree has uncommitted changes.
- `-d unstable` = build against unstable dependencies.
- Run from inside the source repo dir.

Output lands in `..` (parent of the repo dir): `<pkg>_<ver>_source.changes`, `.dsc`, `.tar.xz`, plus arch-specific `.build`, `.buildinfo`, `.changes` for each built arch.

### 3. Sign the source .changes

```bash
debsign -k<KEYID> ../<pkg>_<ver>_source.changes
```

- Use the long keyid. Example: `debsign -k0xC517C25DE408759D98A4C96B6C8F74AE87700B7E ../bpfcc_0.37.0+ds-1_source.changes`.
- If `debsign` without `-k` picks the wrong key, specify it explicitly.
- Verify the signature: `debsign -v ../<pkg>_<ver>_source.changes` (or check the accompanying `.signature` file).

### 4. Upload to ftp-master

```bash
dput ftp-master ../<pkg>_<ver>_source.changes
```

- `ftp-master` is the dput profile name from `~/.dput.cf` / `/etc/dput.cf` — it resolves to `ftp.upload.debian.org`, incoming `/pub/UploadQueue/`, method `ftp`, login `anonymous`.
- The upload goes to the Debian queue; acceptance to unstable is separate (see verification below).

### 5. Tag after successful upload

```bash
gbp buildpackage --git-tag-only --git-sign-tags
```

- Run after the upload is accepted — tags the release in the local git history.
- Do NOT tag before the upload is confirmed accepted; a premature tag can desync from what actually reached the archive.

## Verify upload acceptance

After uploading, confirm the package reached unstable:

1. **Tracker:** `https://tracker.debian.org/pkg/<source-pkg>` — check the "unstable" version line. Wait for it to show the new version.
2. **News section** on the tracker page — look for "Accepted bpfcc <version> (source) into unstable" news entry.
3. **Buildd:** `https://buildd.debian.org/status/package.php?p=<source-pkg>&suite=unstable` — once accepted, buildd picks up the new source and starts building across architectures.

## Read buildd status

Once the package is in unstable, monitor/build-verify on buildd.debian.org:

### Fetch the status page

```bash
curl -sL "https://buildd.debian.org/status/package.php?p=<source-pkg>&suite=unstable" -o /tmp/<pkg>_buildd.html
```

### Parse architectures

Each `<tr>` row in the table contains:
- Architecture link: `architecture.php?a=<arch>&suite=sid`
- Version
- Status cell with `status-<state>` class and `title="..."` attribute
- Buildd hostname (if assigned)

Status values:
- `status-installed` — built and installed in the archive.
- `status-buildattempted` — build attempted but failed (look for the linked log).
- `status-needsbuild` — queued, waiting for a buildd.
- `status-1` / `status-buildattempted` with an `id="problem-N"` anchor — failure with a visible log tail on the page.

### Get a failing build log

Use `getbuildlog` (from `devscripts`):

```bash
getbuildlog <pkg> <version> <arch>
```

- Downloads the build log to the current directory as `<pkg>_<ver>_<arch>.log`.
- `-V` / `-v` flag prints the download URL for debugging.
- If `getbuildlog` with an explicit version fails, try `getbuildlog <pkg> last <arch>` — it falls back to fetching the latest build log for that architecture.
- Inspecting the log tail: the failure is usually near the end. Search for `Error`, `error:`, `assertion failed`, `cannot find` to locate the root cause quickly.

### Architecture-specific format string failures

On architectures where `unsigned long != unsigned long long` (ppc64el, loong64, riscv64), `__u64` is typedef'd to `unsigned long`, causing `-Werror=format` failures when using `%llu`/`%lld`. Fix by:

1. Add `#include <inttypes.h>`
2. Use `PRIu64`/`PRId64`/`PRIx64`/`SCNu64` macros with explicit `(uint64_t)` cast for `printf`/`scanf` format strings
3. Example: `printf("%" PRIu64 "\n", (uint64_t)val);`

When a new failure appears in the same class as an existing patch (e.g., another `__u64` format string), check whether the patch covers all affected files — grep for `%llu`/`%lld` in the relevant source directory and compare against the patch file list.

### Distinguish bug categories from build logs

A build log failure may look like a known BTS bug but be a different root cause:
- **FTBFS bug title may misattribute the cause.** Bug #1133435 was titled "ftbfs with GCC-16" but the actual ppc64el failure was LuaJIT `bcsave.lua:247: assertion failed!` — a LuaJIT/ppc64le bytecode-saving issue, not GCC-16.
- **Verify the toolchain version in the log** (look for `gcc-16`, `g++-16` in the build environment section) before concluding a GCC-version bug is the cause.
- **Check where the build stops.** If compilation proceeds well past the claimed failure point (e.g. 15% built with no GCC errors), the real failure is elsewhere — read the log, don't trust the BTS title.
- **Separate bugs should not be mashed into one comment.** If the BTS bug is about GCC-16 and the log shows a LuaJIT crash, confirm the GCC-16 fix is in the upstream version and note the LuaJIT failure as a separate issue.

## Pitfalls

- **Do NOT tag before upload is accepted.** A premature tag diverges from the archive state; wait for the tracker news entry confirming acceptance.
- **getbuildlog can fail silently with an explicit version.** If `getbuildlog pkg ver arch` returns an error, retry with `getbuildlog pkg last arch` — the explicit version string may not match what buildd stored.
- **The BTS bug title is not always the actual failure.** Read the build log before concluding which bug is responsible. A "GCC-16 FTBFS" bug may turn out to be a LuaJIT assertion on a specific arch.
- **Don't assume all arches build the same.** A package can succeed on amd64/arm64/s390x/loong64/armhf and fail on ppc64el — verify each architecture independently.
- **Needs-Build is not a failure.** riscv64 sitting in Needs-Build means no buildd has picked it up yet — not that it failed. Distinguish from Build-Attempted (failure) and Installed (success).
- **Clean the build artifacts directory after inspection.** Downloaded logs and parsed HTML in /tmp or ~/ can accumulate — remove or archive them when done.
