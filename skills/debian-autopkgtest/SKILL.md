---
name: debian-autopkgtest
description: Add autopkgtest smoke tests to any Debian source package. Covers runner selection (unshare with kernel header bind mounts for packages needing kernel headers at runtime), unprivileged test design, CAP_BPF nuances, runtime prerequisite discovery, and build system detection.
version: 1.1.0
category: debian
author: Vasudev Kamath
license: MIT
metadata:
  hermes:
    tags: [debian, autopkgtest, packaging, ci, sbuild, unshare]
    related_skills: [debian-package-maintenance]
---

# Debian Autopkgtest — Add Smoke Tests

## When to Use

Use when the user asks to:
- Add autopkgtest to a Debian package that has no `debian/tests/` directory
- Create smoke tests for a package's installed binaries, libraries, or Python modules
- Validate that installed `.deb` packages work after installation
- Add `Testsuite: autopkgtest` to `debian/control`

**User constraint (bpfcc):** when `debian/tests/` already has a valid `control` file,
**do NOT** add `Testsuite: autopkgtest` to `debian/control` — it produces a lintian
warning (`unnecessary-testsuite-autopkgtest-field`). Use the existing `debian/tests/`
directory as-is; only add the field if `debian/tests/` is absent.

Do NOT use when:
- The task is about running upstream unit tests (use `dh_auto_test` instead)
- Re-enabling `nocheck` in `debian/rules` (different task)
- Adding `needs-root` tests (this skill covers unprivileged smoke tests only)

## Context

autopkgtest tests the **installed package** on a fresh system, not the source tree. Its job is to catch packaging bugs: missing files, wrong install paths, broken dependencies, broken postinst scripts, import failures.

It is NOT a replacement for upstream unit tests. Upstream tests belong at build time via `dh_auto_test`, which is a separate decision about re-enabling `nocheck` in `debian/rules`.

This skill covers adding minimal smoke tests that validate the installed `.deb` works. Smoke tests exercise the public API of the installed package — imports, basic function calls, CLI `--help`, file presence — without requiring root.

## How to Design Smoke Tests

### Questions to ask

1. **What does the package install?** List binaries, libraries, Python modules, data files.
2. **What can be tested without root?** Imports, function calls, CLI `--help`, file presence, basic operations that don't attach to kernel/tracepoints.
3. **What runtime deps are needed?** Does the package need kernel headers, a specific interpreter, a data file that's in a separate package?
4. **What's the minimum that proves the package works?** Import + one function call. Or binary exists + `--help` exits 0.

### Patterns by package type

**Python package** — test imports and basic API:
```bash
python3 -c "import <module>; print('OK')"
```
Or more thorough: call a function, check return value.

**CLI tool package** — test binary exists and runs:
```bash
<binary> --help > /dev/null 2>&1
```
Or test a non-destructive subcommand.

**Library package** — test the library links and basic operations work:
```bash
# For C libs: check .so exists
ls /usr/lib/*/lib<name>.so

# For Python libs: import and call
python3 -c "from <module> import <func>; <func>()"
```

**Mixed package** (python + CLI + lib) — one test per component:
```bash
# Test python module
python3 -c "import <module>"

# Test CLI tool
<binary> --help

# Test library
ls /usr/lib/*/lib<name>.so
```

## Architecture-aware test design

When the source `debian/control` declares binary packages with architecture restrictions, the test suite must only run where those packages are actually built. This is a common source of `badpkg` failures during CI.

### Read the architecture split first

From `debian/control`'s binary package stanzas, build a map of which packages are built for which architectures:

| Package | Architecture |
|---|---|
| `libbpf-tools` | `amd64 arm64` |
| `bpfcc-introspection` | `amd64 arm64 loong64 ppc64el riscv64` |
| `bpfcc-lua` | `amd64 arm64 s390x armhf` |
| `libbpfcc` | `amd64 arm64 loong64 ppc64el s390x armhf riscv64` |
| `python3-bpfcc` | `all` |
| `bpfcc-tools` | `all` |

Then decide which test stanzas must be restricted.

### Add `Architecture:` to the test stanza

In `debian/tests/control`, add an `Architecture:` field listing the arches where the test's dependencies are built:

```
Tests: libbpf-tools-smoke
Architecture: amd64 arm64
Depends: @, libbpf-tools
```

When the testbed architecture is not in the list, autopkgtest **skips** the test (it does not fail with `badpkg`). This is the correct way to express "this test only makes sense on these arches".

### `@` in `Depends` and architecture-awareness

`@` expands to **all binary packages generated from the source**. If any of those packages is not built for the test architecture, the test will get `badpkg`. If you only need a subset, list them explicitly:

```
Tests: libbpf-tools-smoke
Architecture: amd64 arm64
Depends: libbpf-tools
```

### Example — bpfcc

bpfcc 0.37.0+ds-4 builds `libbpf-tools` only on `amd64 arm64`. The smoke test for that package must be architecture-restricted:

```
# debian/tests/control
Tests: python-smoke
Restrictions: allow-stderr
Depends: @, python3-bpfcc

Tests: libbpf-tools-smoke
Architecture: amd64 arm64
Restrictions: allow-stderr
Depends: @, libbpf-tools

Tests: bpfcc-introspection-smoke
Architecture: amd64 arm64 loong64 ppc64el riscv64
Restrictions: allow-stderr
Depends: @, bpfcc-introspection

Tests: bpfcc-lua-smoke
Architecture: amd64 arm64 s390x armhf
Restrictions: allow-stderr
Depends: @, bpfcc-lua
```

Without the `Architecture:` fields, the `libbpf-tools-smoke`, `bpfx-introspection-smoke`, and `bpfx-lua-smoke` tests would fail with `badpkg` on `armhf`, `i386`, `s390x` (and others) because the corresponding `.deb` is not built there.

### Decision checklist

- [ ] Read `Architecture:` from every binary package stanza in `debian/control`
- [ ] For each test, determine which package(s) it depends on
- [ ] If a dependency is architecture-restricted, add `Architecture:` to the test stanza with the built architectures
- [ ] If a dependency is `all`-arch, no `Architecture:` field is needed
- [ ] Verify with `dpkg -s <pkg>` on a multi-arch host before committing the fix

## Files to Create

### debian/tests/control

One stanza per test suite. Generic pattern:

```
Tests: <name>
Restrictions: allow-stderr
Depends: @, <runtime-deps>
```

- `Tests:` — space-separated test names; maps to executables in `debian/tests/`
- `Restrictions: allow-stderr` — don't fail if the test produces stderr (common for libraries that debug-log)
- `Depends: @` — installs the source package's own binary packages (all of them)
- `Depends: <runtime-deps>` — additional packages needed at test time (e.g. kernel headers, interpreter libs)
- No `needs-root` — unprivileged smoke tests only

**Important: `@` semantics.** In isolated testbeds (chroot/unshare), autopkgtest installs all generated `.deb`s. In null runner with `-B` (`--no-built-binaries`), `dpkg-checkbuilddeps` checks if every binary package from the source is installed on the host — if any are missing, the test fails with `badpkg`. If you only need some binaries, list them explicitly instead of `@`.

Multiple stanzas for different components:

```
Tests: python-smoke
Restrictions: allow-stderr
Depends: @, python3-<pkg>

Tests: cli-smoke
Restrictions: allow-stderr
Depends: @, <cli-package>
```

### debian/tests/<name>

Executable shell script for each test named in `control`. Must be `chmod +x`.

Minimal skeleton:

```bash
#!/bin/sh
set -e

export AUTOPKGTEST_TMP=${AUTOPKGTEST_TMP:-/tmp/adt-smoke}
mkdir -p "$AUTOPKGTEST_TMP"

# Optional: check for runtime prerequisites
if [ ! -f /path/to/required/file ]; then
    echo "FAIL: required file not found — install <package>"
    exit 1
fi

# Run the actual test (inline or call a separate program)
<test commands>

echo "<name>: PASS"
```

### debian/control

**User constraint (bpfcc):** when `debian/tests/` already has a valid `control` file,
**do NOT** add `Testsuite: autopkgtest` to `debian/control` — it produces a lintian
warning (`unnecessary-testsuite-autopkgtest-field`). Use the existing `debian/tests/`
directory as-is; only add the field if `debian/tests/` is absent.

```no-highlight
# For new packages: add to source stanza only
Testsuite: autopkgtest
```

### debian/changelog

Add an entry for the autopkgtest addition. Bump version appropriately.

## Implementation Steps

1. Read this skill in full
2. Create branch (e.g. `deploy/autopkgtest`) from `master`
3. Determine what to test — see "How to Design Smoke Tests" above
4. Create `debian/tests/control` with one stanza per test suite
5. Create `debian/tests/<name>` scripts — one per test named in control
6. Make all scripts executable: `chmod +x debian/tests/*`
7. **User constraint (bpfcc):** do NOT add `Testsuite: autopkgtest` to `debian/control`
   if `debian/tests/` already exists — lintian warning `unnecessary-testsuite-autopkgtest-field`.
8. Update `debian/changelog` (check existing tags first — see Pitfalls)
9. Run each test script manually to verify before building
10. Build the package (use the package's normal build system — see Build System Detection below)
11. Run autopkgtest with the appropriate runner (unshare for rootless; see Runner Selection)
12. Commit: `git add debian/tests/control debian/tests/* debian/changelog && git commit`
13. Push the branch

## Runner Selection

### null runner (`-- null`)

Runs on the host without isolation. **Needs root** for apt-get in the testbed. Without root, fails with "Permission denied".

**Not recommended** for packages needing kernel headers at runtime — the host environment may have them but the testbed setup is fragile.

### unshare runner (`-- unshare`)

**Recommended for most packages.** Rootless, boots an unprivileged test container on demand. No sudo needed.

For packages that compile BPF programs or need kernel headers at runtime (like bcc), bind-mount the kernel build directory:

```
autopkgtest ../<pkg>_<version>_amd64.changes \
  -- unshare -r unstable \
  -b /lib/modules /lib/modules \
  -b /usr/src /usr/src
```

This provides:
1. Complete isolation and clean installation of newly built `.deb` packages.
2. Access to `/lib/modules/$(uname -r)/build` for runtime kernel header needs (bcc/Clang).
3. Clean pass (exit 0) for smoke tests.

The bind mounts are only needed when the package's runtime behavior requires kernel headers beyond what `linux-libc-dev` provides (UAPI headers). For packages that only need UAPI headers, `linux-libc-dev` in `Depends:` is sufficient and no bind mounts are needed.

### schroot runner (`-- schroot <name>`)

Requires sudo + schroot configured. Good for clean chroot builds. Example:

```
sudo autopkgtest ../<pkg>_*.deb -- schroot sid-amd64
```

### qemu runner (`-- qemu <image>`)

Full VM isolation. Slowest but most complete. Requires a qemu image.

### Manual run (no runner)

If no runner is available, run the test scripts directly — they validate the scripts work, but not in a clean testbed:

```bash
debian/tests/<name>
```

## Runtime Prerequisites

Some packages need additional packages at test time that are not in their `Depends:`.

**How to identify:**
1. Run the smoke test manually on a fresh system (or in unshare)
2. Note what's missing
3. Find which package provides the missing file: `dpkg -S /path/to/file` or `apt-file search`
4. Add that package to `Depends:` in the test stanza

**Example (bpfcc):** libbpfcc needs kernel UAPI headers at runtime to compile BPF programs. The package `linux-libc-dev` provides `/usr/include/linux/bpf.h`. Without it, `BPF(text=...)` fails. So `linux-libc-dev` goes in `Depends:` for the python smoke test.

**Example (bpfcc bcc component):** The bcc Python module uses Clang to compile BPF programs at runtime and needs `/lib/modules/$(uname -r)/build`. This is satisfied by bind-mounting `/lib/modules` and `/usr/src` into the unshare testbed. No additional `Depends:` beyond `linux-libc-dev` is needed.

## Build System Detection

Don't assume the build system. Check the package:

- `debian/gbp.conf` present → git-buildpackage: use `gbp buildpackage`
- `debian/` has `source/format` → check format; `3.0 (native)` or `3.0 (quilt)` are common
- No git → `debuild` or `dpkg-buildpackage`

**Common invocations:**

```bash
# git-buildpackage + sbuild (most common for Debian packages with git)
gbp buildpackage --git-builder="sbuild -s -d unstable -c <chroot-name>" --git-ignore-new

# If chroot tarball doesn't exist, sbuild auto-bootstraps via mmdebstrap
gbp buildpackage --git-builder="sbuild -s -d unstable" --git-ignore-new

# Quilt cleanup if build fails midway
quilt pop -a
git restore <patched-dirs>
rm -rf .pc debian/.debhelper debian/debhelper-build-stamp debian/tmp

# Non-git package
debuild -us -uc -b
```

## Rules — Follow Strictly

- DO NOT ship or run upstream test files via autopkgtest
- DO NOT modify `debian/rules` for autopkgtest (independent of build-time `dh_auto_test`)
- DO NOT re-enable `nocheck` (separate decision)
- DO NOT add `needs-root` tests in this iteration
- DO keep tests unprivileged — smoke tests should run without root
- DO check for runtime prerequisites at the start of each test script and fail clearly if missing
- DO keep it minimal — one or two test suites, not a full upstream test suite

## Pitfalls

### CAP_BPF and map creation

On modern Linux kernels, creating BPF maps (`BPF_HASH`, `BPF_ARRAY`, etc.) requires `CAP_BPF` or `CAP_SYS_ADMIN`. Running map operations unprivileged produces:

```
could not open bpf map: counter, error: Operation not permitted
```

**Bytecode compilation and disassembly do NOT require root.** Loading trivial BPF code and disassembling it can succeed unprivileged (on kernels with unprivileged BPF enabled), or can be validated without attaching probes.

**Recommended pattern:** make map operations conditional on `os.getuid() == 0`:

```python
if os.getuid() == 0:
    b_map = BPF(text=b"BPF_HASH(counter, int, int);")
    tbl = b_map.get_table("counter")
    tbl[0] = 42
    assert tbl[0].value == 42
else:
    print("  SKIP: BPF_HASH map (requires root/CAP_BFf)")
```

This preserves the "no needs-root" requirement while still testing map operations when root is available.

### autopkgtest null runner needs root

`autopkgtest ... -- null` runs apt-get update in the testbed, which needs root. Without root, it fails with "Permission denied".

**Use `unshare` instead** for rootless testing. Add bind mounts for packages that need kernel headers at runtime.

### don't add linux-headers-$(uname -r) as a Depends

Kernel-headers packages are kernel-release-specific and cannot be statically resolved by apt. Never add `linux-headers-$(uname -r)` to `Depends:`.

**For UAPI headers:** add `linux-libc-dev` to `Depends:` — it provides `/usr/include/linux/bpf.h` and friends, always available regardless of running kernel.

**For full kernel build tree (bcc/Clang):** use bind mounts (`-b /lib/modules /lib/modules -b /usr/src /usr/src`) in the unshare runner. No `Depends:` needed.

### Tests should be idempotent

autopkgtest may re-run tests. Don't rely on state left by a previous test run. Clean up after yourself or use `$AUTOPKGTEST_TMP`.

### allow-stderr is often needed

Many libraries print debug info to stderr on normal operation. `Restrictions: allow-stderr` prevents false failures.

### Don't test upstream code via autopkgtest

autopkgtest tests the **installed package**, not the upstream source. Running upstream's test suite is `dh_auto_test` at build time — a different mechanism.

### Changelog versioning — check tags first

Before writing the changelog entry, check `git tag` to see what versions are already released. If `debian/<version>-1` is already tagged, increment to `<version>-2`.

### Build agent may not know the package build system

An AI agent handed this skill might try `dpkg-buildpackage` when the package uses `gbp buildpackage`, or vice versa. Include the package's actual build command, or instruct the agent to check `debian/gbp.conf` for build system clues.

### Lintian: don't add Testsuite field when tests/ already exists

When `debian/tests/` already has a valid `control` file, **do not** add
`Testsuite: autopkgtest` to `debian/control` — the package triggers:

```
W: <pkg> source: unnecessary-testsuite-autopkgtest-field [debian/control:40]
```

Use the existing `debian/tests/` directory as-is. Add the field only if
`debian/tests/` is absent.

### autopkgtest unshare runner scratch directory

mmdebstrap (the testbed bootstrap) runs as the autopkgtest process user and
creates its tarball in the scratch directory. If the scratch dir is not
writable by that user, the whole run fails at testbed setup (exit 16), before
any test runs:

```
E: cannot create <scratch>/mmdebstrap.<hash>: Permission denied
autopkgtest: ERROR: testbed failure: eof from the virtualisation server
```

**Fix:** run autopkgtest with a scratch dir that the autopkgtest process can
write to. Check `ps` output during the run to see the effective user, or use a
global temp dir like `/tmp` or an environment variable override:

```bash
# Verify the effective user of the autopkgtest process
ps -o user=,group= -p <autopkgtest-pid>

# Run from a world-writable scratch dir (e.g. /tmp) instead of ~/.hermes/cache
AUTOPKGTEST_TMP=/tmp/adt-<pkg> autopkgtest <pkg>_*.changes -- unshare -r unstable
```

**Never** point autopkgtest at a directory owned by another user or with
restrictive permissions (e.g. `700` owned by `vasudev` when the process runs as
`nobody`/`100000`). The directory must be writable by the effective autopkgtest
user.

### `@` in Depends can cause badpkg failures

If using null runner with `-B` (no-built-binaries), `@` expands to all binary packages. If any are not installed on the host, the test fails with `badpkg`. Use explicit package names if you only need some binaries.

## Reference Files

- `references/control` — generic example `debian/tests/control`
- `references/skeleton.sh` — minimal test script skeleton

## Checklist

- [ ] Read this skill in full
- [ ] Create branch from `master`
- [ ] Determine what to test (binaries, libs, Python modules — whatever the package installs)
- [ ] Identify runtime prerequisites (run test manually, check `dpkg -S` for missing files)
- [ ] Create `debian/tests/control` with appropriate stanzas
- [ ] Create test scripts in `debian/tests/`
- [ ] Make scripts executable
- [ ] **User constraint (bpfcc):** do NOT add `Testsuite: autopkgtest` to `debian/control`
      if `debian/tests/` already exists (lintian warning)
- [ ] Update `debian/changelog` (check tags first for version bump)
- [ ] Run each test script manually to verify
- [ ] Build the package (detect build system first)
- [ ] Run autopkgtest with appropriate runner (unshare for rootless; see Runner Selection)
- [ ] Commit
- [ ] Push

## References

- `references/control` — generic example `debian/tests/control`
- `references/skeleton.sh` — minimal test script skeleton with runtime prerequisite check pattern

## After adding autopkgtest

Once ATE is in place and the package builds, the next step is often monitoring test results on debci. Use the `debci-api` skill to submit the package for CI testing or check existing results:

```bash
# Check if debci already has results
bash ~/.hermes/skills/debian/debci-api/scripts/debci.sh pkg-results <package>

# Submit for CI testing (only if ATE exists in debian/control)
bash ~/.hermes/skills/debian/debci-api/scripts/debci.sh submit unstable amd64 <package> 8
```
