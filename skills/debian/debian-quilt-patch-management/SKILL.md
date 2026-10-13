---
name: debian-quilt-patch-management
version: '1.0'
author: 'Vasudev Kamath'
license: 'MIT'
category: debian
description: Use when editing Debian patches with quilt.
tags:
  - debian
  - quilt
  - packaging
  - patches
related_skills:
  - debian-package-maintenance
  - debian-build-failure-analysis
  - gbp-upstream-push
---

## When to Use

Use when working with Debian source packages that use quilt for patch management (packages with `debian/patches/` and a `series` file, `debian/source/format` = `3.0 (quilt)`).

# Debian Quilt Patch Management

## Quick Reference

| Task | Command |
|------|---------|
| Apply all patches | `quilt push -a` |
| Unapply all patches | `quilt pop -a` |
| Add file to current patch | `quilt add <file>` |
| Create new patch | `quilt new <patch-name>` then `quilt add <file>` |
| Refresh current patch | `quilt refresh` |
| Show applied patches | `quilt applied` |
| Show unapplied patches | `quilt unapplied` |
| Edit file (auto-adds to patch) | `quilt edit <file>` |
| View current patch diff | `quilt diff` |

## Workflow: Fix a Build Failure by Updating an Existing Patch

```bash
# 1. Enter package source directory
cd /path/to/package-source

# 2. Apply all patches so source reflects patched state
quilt push -a

# 3. Identify which patch to update (usually the last one for format fixes)
quilt applied

# 4. Add the missing file to that patch
quilt add libbpf-tools/biopattern.c

# 5. Edit the file to fix the issue
# (use your editor or patch tool)

# 6. Refresh the patch to include your changes
quilt refresh

# 7. Verify the patch looks correct
quilt diff

# 8. Test: unapply and reapply all patches
quilt pop -a && quilt push -a
```

## Workflow: Create a New Patch

```bash
# 1. Apply existing patches first
quilt push -a

# 2. Create new patch (will be added to series after the last applied)
quilt new 2005-fix-new-issue.patch

# 3. Add files you'll modify
quilt add file1.c file2.h

# 4. Make your changes
# ... edit files ...

# 5. Refresh to finalize
quilt refresh
```

## Important: Patch Naming Convention

- **Numbered patches** (2001, 2002, etc.): Debian-specific fixes, ordered by priority
- **Upstream patches** (0001, 0002, etc.): Cherry-picked from upstream, `git format-patch` style
- **Descriptive names**: `fix-install-path.patch`, `libbpf-tools-debian.patch`
- Always end with `.patch`

## Common Pitfalls

1. **Forgetting `quilt add` before editing**: The file won't be tracked. Use `quilt edit <file>` which adds + opens editor.

2. **Editing files while patches are unapplied**: Changes go to orig/ not the patch. Always `quilt push -a` first.

3. **Wrong indentation in diffs**: Match the surrounding code style (tabs vs spaces). Check with `quilt diff`.

4. **Not refreshing after edits**: `quilt refresh` updates the patch file in `debian/patches/`.

5. **Modifying patches directly in debian/patches/**: Always work through quilt so `series` and patch headers stay consistent.

## Advanced: Updating a Patch That Isn't the Topmost

```bash
# Pop to the patch you want to modify
quilt pop 2004-fix-u64-format-strings.patch

# Now it's the topmost applied patch
quilt add libbpf-tools/biopattern.c
# ... edit ...
quilt refresh

# Re-apply remaining patches
quilt push -a
```

## Integration with Debian Build

- Patches in `debian/patches/series` are applied automatically by `dpkg-source` during build
- The `debian/source/format` must be `3.0 (quilt)` (standard for modern packages)
- `debian/rules` typically doesn't need explicit quilt calls

## Useful Aliases (add to ~/.bashrc)

```bash
alias qpush='quilt push -a'
alias qpop='quilt pop -a'
alias qdiff='quilt diff'
alias qadd='quilt add'
alias qnew='quilt new'
alias qrefresh='quilt refresh'
alias qedit='quilt edit'
```

## Related Skills

- `debian-package-maintenance`: Full Debian package maintenance workflow
- `debian-build-failure-analysis`: Diagnose FTBFS from build logs
- `gbp-upstream-push`: Git-based workflow with gbp