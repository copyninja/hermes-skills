---
title: debian-autopkgtest
description: "Add autopkgtest smoke tests to Debian source packages."
name: debian-autopkgtest
version: 1.1.0
author: Vasudev Kamath (@vkamath), Hermes Agent
license: MIT
hermes:
  tags: [debian, autopkgtest, packaging, ci, sbuild, unshare]
  related_skills: [debian-package-maintenance]
---

# Debian Autopkgtest Skill

Add autopkgtest smoke tests to a Debian source package, so the installed .deb is
validated on a fresh system.

## When to Use

- Add autopkgtest to a Debian package that has no `debian/tests/` directory.
- Create smoke tests for installed binaries, libraries, or Python modules.
- Validate that installed .deb packages work after installation.
- Add `Testsuite: autopkgtest` to `debian/control`.

## Prerequisites

- The package's `debian/` tree is prepared.
- `linux-libc-dev` (for runtime UAPI headers) if the package needs kernel
  headers.
- For packages that compile BPF programs at runtime: bind mounts for
  `/lib/modules` and `/usr/src` in the unshare runner.
- `debian/tests/control` and test scripts when adding ATE.

## How to Run

1. Read this skill in full.
2. Create a branch (for example `deploy/autopkgtest`) from `master`.
3. Determine what to test (binaries, libs, Python modules).
4. Create `debian/tests/control` with one stanza per test suite.
5. Create test scripts in `debian/tests/` (one per test named in control).
6. Make scripts executable.
7. Build the package and run autopkgtest with the appropriate runner.
8. Commit and push.

## Quick Reference

- Runner selection: `null` (needs root), `unshare` (rootless; bind mounts for
  kernel headers), `schroot`, `qemu`, or manual run.
- Runtime UAPI headers: add `linux-libc-dev` to `Depends:`.
- Full kernel build tree (bcc/Clang): bind-mount `/lib/modules` and `/usr/src`.
- Never add `linux-headers-$(uname -r)` to `Depends:`.
- Find which package provides a missing file with search_files.

## Procedure

1. Read this skill in full.
2. Create a branch.
3. Determine what to test.
4. Create `debian/tests/control`.
5. Create test scripts.
6. Make scripts executable.
7. Build the package.
8. Run autopkgtest with the appropriate runner.
9. Commit and push.

## Pitfalls

- CAP_BPF and map creation require `CAP_BPF` or `CAP_SYS_ADMIN` when running
  unprivileged. Make map operations conditional on `os.getuid() == 0`.
- The autopkgtest null runner needs root for apt-get in the testbed. Use `unshare`
  instead.
- Do not add `linux-headers-$(uname -r)` to `Depends:`.
- Tests should be idempotent; use `$AUTOPKGTEST_TMP` and clean up.
- `allow-stderr` is often needed (libraries debug-log to stderr).
- Do not test upstream code via autopkgtest (that is `dh_auto_test` at build
  time).
- Check git tags before bumping the changelog (`debian/<version>-1` already
  tagged → increment to `-2`).

## Verification

- Run each test script manually before building.
- Build the package.
- Run autopkgtest with the appropriate runner (unshare for rootless).
- Commit and push.

## Reference Files

- `references/control` — generic example `debian/tests/control`.
- `references/skeleton.sh` — minimal test script skeleton with runtime
  prerequisite check pattern.
