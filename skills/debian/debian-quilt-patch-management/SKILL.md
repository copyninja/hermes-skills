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
quilt add path/to/file.c

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
quilt pop <patch-name>.patch

# Now it's the topmost applied patch
quilt add path/to/file.c
# ... edit ...
quilt refresh

# Re-apply remaining patches
quilt push -a
```

## Workflow: Regenerate Patch When Source Was Edited Outside Quilt

If you edited a source file directly (not via `quilt edit`/`quilt add`) and need to update the patch:

```bash
# 1. Restore original file from git
cd /path/to/package-source
git checkout path/to/file.c

# 2. Apply all patches (this applies the OLD patch)
quilt push -a

# 3. Make the fix to the now-patched file
# ... edit file.c ...

# 4. Refresh the patch to capture the new diff
quilt refresh

# 5. Verify: unapply and reapply all patches
quilt pop -a && quilt push -a
```

**Why**: Quilt tracks changes from the orig/ directory. If you edit the file while patches are unapplied, your changes go to the working tree but quilt's orig/ still has the old version. Restoring from git first ensures quilt sees the correct baseline.

## Handling Failed Hunk Application

When `quilt push` fails with "Hunk #N FAILED":

```bash
# 1. Check the reject file
cat path/to/file.c.rej

# 2. Manually apply the rejected hunk to the source file
# ... edit file.c ...

# 3. Remove the reject file
rm path/to/file.c.rej

# 4. Refresh the patch
quilt refresh
```

The reject file shows the exact diff that failed — apply it manually, then refresh.

## Format String Fixes for Architecture-Portable Code

When fixing printf/scanf format warnings for integer types that vary across architectures (e.g., `__u64`, `__s64`, `uint64_t`, `int64_t` on ppc64el, loong64, riscv64 where `unsigned long` != `unsigned long long`):

1. Add `#include <inttypes.h>`
2. Use format macros instead of hardcoded specifiers:
   - `PRIu64` / `PRId64` / `PRIx64` / `PRIo64` for printf
   - `SCNu64` / `SCNd64` / `SCNx64` / `SCNo64` for scanf
3. Cast to `uint64_t` / `int64_t` when using the macros
4. Examples:
   - Unsigned: `printf("%" PRIu64 "\n", (uint64_t)value);`
   - Signed: `printf("%" PRId64 "\n", (int64_t)value);`
   - Hex: `printf("%" PRIx64 "\n", (uint64_t)value);`
   - scanf: `fscanf(f, "%" SCNu64 "\n", &value);`

**Why**: On ppc64el, `__u64` is `unsigned long` (64-bit), not `unsigned long long`. `%llu` expects `unsigned long long` → format mismatch. `PRIu64` expands to the correct specifier for the platform (`lu` on ppc64el, `llu` on x86_64). The cast ensures the argument type matches the format exactly.

### x86_64 Specific Gotcha

On x86_64, `PRIu64` expands to `%lu` (expects `unsigned long`), but `__u64` / `uint64_t` is `unsigned long long`. **Always cast explicitly**:
```c
printf("%-10" PRIu64, (uint64_t)counts[i]);  // Correct
printf("%-10" PRIu64, counts[i]);             // Wrong on x86_64
```

## Complete Workflow: Fix Build Failures Across Multiple Files

```bash
# 1. Push the target patch
quilt push <patch-name>.patch

# 2. For each new file with errors:
quilt add path/to/file.c
# ... edit file (add necessary headers, fix issues) ...

# 3. After all files fixed:
quilt refresh <patch-name>.patch

# 4. Commit
quilt pop -a  # verify clean apply
quilt push -a
git add debian/patches/<patch-name>.patch
git commit -m "debian/patches/<patch-name>: <description>"
```

## Squashing Multiple Incremental Commits

If you made many small commits while fixing each file:

```bash
git log --oneline  # find base commit before the series
GIT_SEQUENCE_EDITOR="sed -i '2,\$s/^pick/squash/'" git rebase -i <base-commit>^
# If editor fails:
git commit --no-edit -m "<comprehensive message covering ALL fixed files>"
# For final fix (e.g., x86_64 cast):
git commit --amend --no-edit
```

**Lesson**: Squash into ONE commit with message listing ALL files fixed. Keeps history clean.

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
