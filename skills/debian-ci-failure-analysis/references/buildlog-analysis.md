# Buildlog Analysis

## Decision: which log do I need?
- CI per-job autopkgtest test log (why `autopkgtest` failed): **not** on the public UI; requires auth.
- Source-package build log (why `dpkg-buildpackage`/`binary-arch` failed): buildd.debian.org via `getbuildlog`. Use when the package fails to build on an arch.

## getbuildlog (devscripts)
```bash
getbuildlog <pkg> <ver> <arch>
getbuildlog bpfcc 0.37.0+ds-4 ppc64el
```
Saves as `<pkg>_<ver>_<arch>.log` in CWD. Needs wget + network to buildd.debian.org.

## Manual wget fallback
Failing builds (bpfcc 0.37.0+ds-4):
`https://buildd.debian.org/status/fetch.php?pkg=bpfcc&arch=ppc64el&ver=0.37.0%2Bds-4&stamp=<s>&raw=1`

## Common FTBFS root causes (bpfcc)
| Arch | Symptom | Root cause | State |
| ppc64el | luajit bcsave.lua:247 assertion; bcc.o missing | LuaJIT bpf save bug | fixed upstream in 0.37.0 |
| gcc-16 / llvm21 | .o compile failure | toolchain ABI/wire-type change | fixed upstream in 0.37.0 |
