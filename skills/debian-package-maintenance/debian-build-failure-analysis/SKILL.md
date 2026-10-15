---
name: debian-build-failure-analysis
description: Analyze Debian FTBFS on arches via buildlog and AI.
version: 0.1.0
author: Vasudev Kamath
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [debian, build-failure, buildlog, analysis, ppc64el, luajit]
    related_skills: [debian-package-monitor, autonomous-ai-agents:codex, autonomous-ai-agents:claude-code]
---

# Debian Build Failure Analysis

Reusable workflow to fetch build logs from buildd.debian.org, identify failure patterns, and delegate structured root-cause analysis to an AI coding agent.

## When to Use
- A Debian package fails to build on specific architectures (ppc64el, loong64, riscv64, etc.)
- Need to understand root cause of FTBFS (Fail To Build From Source)
- Want structured analysis with fix recommendations for Debian packaging

## Prerequisites
- `getbuildlog` (from devscripts package) installed
- Access to an AI coding agent (codex, claude-code) via `delegate_task`
- Package name and target architecture known

## Procedure

### 1. Fetch Build Log
```bash
getbuildlog <package> [version] <arch>
```
- `version`: use `last` for latest build attempt, or specific version (e.g. `0.37.0+ds-5`)
- `arch`: target architecture (e.g. `ppc64el`, `loong64`, `riscv64`)
- Output: `<package>_<version>_<arch>.log` in current directory
- Exit code 1 if no matching build found

### 2. Locate Failure in Log
Search for key patterns:
```bash
grep -n -i 'error\|fail\|assertion\|cannot find' <logfile>
```
Focus on the first error that stops the build (not cascading failures).

### 3. Delegate Structured Analysis
Use `delegate_task` with a structured output schema:
```json
{
  "analysis": "string",
  "root_cause": "string",
  "possible_fixes": ["string"],
  "recommended_fix": "string",
  "debian_package_changes": "string"
}
```

Provide context:
- Package name and version
- Architecture
- Key error excerpt from log
- Full log file path
- Source package location (if local)
- Known history (similar failures on other arches)

### 4. Apply Fixes
Based on analysis, implement changes to:
- `debian/rules` (build flags, architecture-specific overrides)
- `debian/control` (Build-Depends, architecture restrictions)
- `debian/patches/` (upstream patches)
- `debian/tests/control` (autopkgtest architecture restrictions)

## Known Failure Patterns

### LuaJIT bcsave.lua Assertion (ppc64el, loong64, riscv64, ppc64)
**Error**: `/usr/bin/luajit: /usr/share/luajit-2.1/jit/bcsave.lua:247: assertion failed!`
**Context**: Bytecode generation (`luajit -b/-bgd`) fails during build
**Root cause**: LuaJIT bytecode writer has architecture-specific bugs in bcsave.lua
**Fixes**:
1. Disable bytecode generation for affected arches (use interpreted Lua)
2. Pre-generate bytecode on a working arch and ship it
3. Patch luajit (upstream fix preferred)
4. Restrict package architectures in debian/control to exclude broken arches

### BlazeSym / Rust linking failures
**Error**: `cannot find -lblazesym` or submodule fetch failures
**Fix**: Update submodule, patch Cargo.toml, or disable optional features

## Pitfalls
- **Cascading errors**: First error is the real cause; later errors are consequences (missing .o files, linker errors)
- **Architecture-specific**: Failure may only manifest on specific arches; test locally with qemu-user if possible
- **Upstream vs packaging**: Determine if fix belongs upstream (patch sent to bcc/iovisor) or in Debian packaging
- **getbuildlog version arg**: `last` gets latest attempt; specify version for historical comparison

## Verification
- After fix, rebuild source package: `dpkg-buildpackage -S -sa`
- Test build locally on target arch (if possible) or request buildd give-back
- Monitor buildd status via debci or package tracker
