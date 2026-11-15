---
name: debian-personal-workflows
version: 1
summary: Vasudev's personal Debian packaging workflows
category: debian
description: Use when packaging Vasudev's packages.
author: Vasudev Kamath
license: MIT
metadata:
  hermes:
    tags: [debian, packaging, quilt, gbp, autopkgtest, bpfcc, fonts]
    related_skills: [debian-package-maintenance, debian-autopkgtest, debian-build-failure-analysis, gbp-upstream-push]
---

## When to Use

- Packaging Vasudev's packages (fonts-*, bpfcc, baresip, cargo, zfec, foolscap, pugixml, smartctl-exporter)
- Large quilt patches (30+ files) that cause `quilt push -a` to loop
- BPF packages needing kernel headers for autopkgtest (bcc, libbpf-tools)
- __u64 format string fixes for ppc64el/loong64/riscv64
- gbp import-orig workflow for GitHub-tagged upstream releases
- Porterbox testing before uploading ppc64el fixes
- Font package specifics (fontconfig triggers, dh_fontconfig)
- Go packages needing both `autopkgtest-pkg-go` (unit tests) and `autopkgtest` (binary smoke tests)
- Prometheus exporter packages (smartctl_exporter, etc.) needing custom autopkgtest smoke tests

# Vasudev's Personal Debian Packaging Workflows

## 1. Large Multi-File Quilt Patch Regeneration

**Problem:** `quilt push -a` loops infinitely on patches touching 30+ files (bpfcc format string fix across 30+ libbpf-tools files).

**Workaround:**
```bash
quilt pop -a && git checkout -- .
patch -p1 < debian/patches/2004-fix-u64-format-strings.patch
# verify
git diff -- libbpf-tools/ ':(exclude)libbpf-tools/Makefile' > debian/patches/2004-fix-u64-format-strings.patch
quilt push -a
```

**Lesson:** Never `quilt refresh` on large patches. Use `git diff` to regenerate.

---

## 2. BPF autopkgtest with Kernel Headers (Rootless)

**Problem:** bcc, libbpf-tools need `/lib/modules/$(uname -r)/build` for Clang/BCC BPF compile.

**Solution (rootless, no sudo):**
```bash
autopkgtest ../<pkg>_<ver>_amd64.changes \
  -- unshare -r unstable \
  -b /lib/modules /lib/modules \
  -b /usr/src /usr/src
```
Bind-mounts host kernel build tree into testbed.

**Discovered:** 2026-09-29 via agy during bpfcc autopkgtest.

---

## 3. __u64 Format String Fix for ppc64el/loong64/riscv64

**Problem:** `__u64` printf breaks where `unsigned long != unsigned long long`.

**Fix:** Use `PRIu64` from `<inttypes.h>`.

**Applied in:** bpfcc 0.37.0+ds-5, patch `2004-fix-u64-format-strings.patch` (30+ files).

```c
#include <inttypes.h>
printf("value: %" PRIu64 "\n", u64_var);
```

**Arches affected:** ppc64el, loong64, riscv64.

---

## 4. gbp import-orig Workflow

```bash
gbp import-orig --uscan --debian-branch=debian/sid --upstream-branch=upstream ../<pkg>_<newver>.orig.tar.xz
```

**Push upstream branch if diverged:** `gbp upstream-push` (see `gbp-upstream-push` skill).

---

## 5. Porterbox Testing for ppc64el

**Reference:** https://dsa.debian.org/doc/porterbox/

**Test before upload:**
```bash
ssh ppc64el.porter.debian.org sbuild -d unstable -A -a ppc64el ../<pkg>_<ver>.dsc
# or
pbuilder --build --distribution unstable --architecture ppc64el ../<pkg>_<ver>.dsc
```
Check build logs for arch-specific failures.

---

## 6. Font Packages (66 packages, fonts team)

- `fontconfig` triggers, `debian/install` font dir structure
- `dh_fontconfig` (debhelper compat 13+)
- GitHub tag releases → `gbp import-orig --uscan`

---

## 7. Architecture-Specific Quirks

| Arch | Quirk |
|------|-------|
| ppc64el | `__u64` needs `PRIu64` |
| loong64 | Same |
| riscv64 | Same |
| arm64 | `%lu` OK for `__u64` |
| amd64 | `%lu` works |

---

## Quick Commands

```bash
# Regen large quilt patch
git diff -- <path> ':(exclude)<path>/Makefile' > debian/patches/<name>.patch

# BPF autopkgtest rootless
autopkgtest ../<pkg>_<ver>_amd64.changes -- unshare -r unstable -b /lib/modules /lib/modules -b /usr/src /usr/src

# Porterbox test
ssh ppc64el.porter.debian.org sbuild -d unstable -A -a ppc64el ../<pkg>_<ver>.dsc

# gbp import upstream
gbp import-orig --uscan --debian-branch=debian/sid --upstream-branch=upstream ../<pkg>_<newver>.orig.tar.xz
```

---

## 8. Go Package autopkgtest (smartctl-exporter pattern)

**Problem**: Go packages need both Go unit tests (`autopkgtest-pkg-go`) and binary smoke tests (`autopkgtest`) in Testsuite.

**Solution**: Add both to `debian/control`:
```
Testsuite: autopkgtest-pkg-go, autopkgtest
```

**Smoke test template** (`debian/tests/smartctl-exporter-smoke`):
- Binary existence check
- `--help` / `--version` exit codes
- Flag parsing with actual binary flags (no `--dry-run`, `--no-collector.smart`)
- Systemd unit verification (check both `/lib` and `/usr/lib` paths)
- Device/service dry-run with background process + `kill`/`wait` + `|| true`

**Lintian warning**: `unnecessary-testsuite-autopkgtest-field` is a false positive when both testsuites are needed. Keep both.

**Local test**:
```bash
export AUTOPKGTEST_TMP=/tmp/autopkgtest-tmp
TMPDIR=/tmp/autopkgtest-tmp
autopkgtest ../<pkg>_<ver>.dsc -- unshare --release=unstable
```

---

## 9. Debian Package Monitoring Pipeline

Complete pipeline: **Acceptance → Buildd → debci CI**

**Three stages**:
1. **Acceptance** — `rmadison` (authoritative archive query), check `unstable` suite
2. **Buildd** — `getbuildlog` across all arches, parse `Status: successful`/`failed`/`Needs-Build`
3. **debci CI** — debci API autopkgtest results (only if `Testsuite: autopkgtest` in control)

**Scripts in `debian-package-pipeline-monitor` skill**:
- `monitor-pipeline.sh` — orchestrates all three stages
- Uses sub-skills: `debian-acceptance-monitor`, `debian-buildd-monitor`, `debian-debci-monitor`

**Cron job**: `schedule: "30m"`, `script: "monitor-pipeline.sh"`, `continuity: true`

---

## 10. Buildd Monitoring Debugging Lessons

- `getbuildlog` saves to **current working directory** — must run from `/tmp`
- `getbuildlog` saves with `.N` suffix — find actual log via `ls -t /tmp/<pkg>_<ver>_<arch>.log* | head -1`
- `getbuildlog` can hang — wrap with `timeout 60`
- Build logs contain `Status: successful` / `Status: failed` and `Finished at` lines
- `rmadison` output uses `|` delimiter — parse with `awk -F'|'`
- `rmadison` columns: `pkg | version | suite | component` (split on `|`, trim spaces)

**Working buildd check**:
```bash
cd /tmp && timeout 60 getbuildlog <pkg> <ver> <arch>
LOGFILE=$(ls -t /tmp/<pkg>_<ver>_<arch>.log* | head -1)
grep "Status: successful" "$LOGFILE"
```