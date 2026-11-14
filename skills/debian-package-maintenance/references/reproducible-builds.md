# Reproducible Build Fixes in Debian Packages

## When to Use

When a package fails `reproduce.debian.net` verification (shows "BAD" for a specific architecture/binary) or when `diffoscope` output from a rebuild shows differences between builds. This is a common blocker for migration to testing/unstable.

## Investigation Workflow

### 1. Check reproduce.debian.net excuses

```bash
# Web: https://reproduce.debian.net/excuses.html?source_name=<source-package>
# Or via API:
web_extract "https://reproduce.debian.net/excuses.html?source_name=<source-package>"
```

- Look for `[BAD]` entries — these are the failing binary packages.
- Note the architecture (e.g., arm64) and binary package (e.g., libbpf-tools).
- Click the diffoscope link for the detailed comparison.

### 2. Analyze diffoscope output

Key differences to look for:

| Difference Type | Likely Cause |
|----------------|--------------|
| Different `.note.gnu.build-id` (Build ID) | Binary content differs → non-deterministic build |
| Symbol ordering differences in `strings` output | Hash table iteration order varies (BTF, skeleton generation) |
| `.rodata` / `.text` byte differences | Compiler non-determinism, uninitialized memory, timestamp embedding |
| Different timestamps in binary | `__DATE__` / `__TIME__` macros, build timestamp embedding |
| File size differences | Different compression, different code paths, locale effects |

### 3. Common non-determinism sources in C/C++/BPF builds

1. **Parallel build races** (`make -jN`) — Concurrent jobs writing to shared state, non-deterministic file system ordering
2. **Locale-dependent output** — `sort`, `date`, compiler messages, `bpftool gen skeleton` BTF type iteration
3. **Timestamps** — `__DATE__`, `__TIME__`, `__TIMESTAMP__`, build system embedding current time
4. **Hash table iteration** — `bpftool gen skeleton`, Clang BPF backend, LLVM internal maps
5. **File system ordering** — `find`, `wildcard`, `ls` without explicit sort
6. **Uninitialized memory** — Stack/heap data leaking into binary
7. **Random seeds** — Compiler optimizations using random seeds (rare, but possible)

### 4. Architecture-specific patterns

- **arm64**: Often shows Clang/LLVM BPF backend non-determinism; `bpftool` BTF type ordering differs from amd64
- **ppc64el/loong64/riscv64**: Format string issues (`__u64` vs `unsigned long`)
- **s390x**: Similar to ppc64el for integer type sizes

## Fix Strategies

### Force single-threaded, locale-stable build

In `debian/rules` or the upstream Makefile:

```make
# In debian/rules override_dh_auto_build or similar:
LC_ALL=C MAKEFLAGS=-j1 make ...

# Or in upstream Makefile (if patching there):
MAKEFLAGS := -j1
unexport MAKEFLAGS
```

### Canonicalize tool output

For tools producing non-deterministic text output (like `bpftool gen skeleton`):

```make
$(OUTPUT)/%.skel.h: $(OUTPUT)/%.bpf.o
	LC_ALL=C $(BPFTOOL) gen skeleton $< | \
		LC_ALL=C sort -u -k2,2 > $@
```

- `LC_ALL=C` forces C locale for consistent sorting
- `sort -u -k2,2` removes duplicates and sorts by the second field (type name/key)
- Adjust sort key based on actual output format

#### bpftool gen skeleton specific notes

`bpftool gen skeleton` emits BTF type definitions and BPF bytecode in hash-table iteration order, which varies between runs (different pointer addresses on arm64). The `sort -u -k2,2` canonicalizes by the second column (type name/identifier). For other tools, inspect the output format and choose the appropriate sort key.

**Why this works**: The skeleton header contains BTF type IDs and names. The first column is typically the type ID (which varies), the second is the type name (which is stable). Sorting by name produces deterministic output regardless of hash iteration order.

### Remove timestamps

- Ensure no `__DATE__`, `__TIME__`, `__TIMESTAMP__` in source
- Check for build system embedding timestamps (CMake `BUILD_TIMESTAMP`, etc.)
- Use `SOURCE_DATE_EPOCH` for reproducible timestamps (Debian sets this automatically)

### Fix archive member ordering

For static libraries linked into multiple binaries:

```make
# Ensure deterministic ar member order
ar rc $(LIBBPF_OBJ) $(sort $(OBJECTS))
```

### Fix format strings for architecture portability

See `debian-quilt-patch-management` skill: "Format String Fixes for Architecture-Portable Code" section.

## Creating the Fix Patch

### 1. Apply existing patches

```bash
cd ~/Documents/Debian/<source-package>
quilt push -a
```

### 2. Create new patch

```bash
quilt new 2005-fix-reproducibility.patch
quilt add path/to/Makefile  # or other files to modify
```

### 3. Make changes

- Edit the Makefile / build scripts
- Add the deterministic build flags
- Follow the project's existing style (tabs, variable naming)

### 4. Refresh and verify

```bash
quilt refresh
quilt pop -a && quilt push -a  # verify clean apply
```

### 5. Test locally (if possible)

```bash
# Build in a clean environment
sbuild --arch=arm64 -d unstable  # or use pbuilder/cowbuilder
# Or test the specific target:
make -C libbpf-tools clean && make -C libbpf-tools V=1
```

### 6. Test on porter box

```bash
ssh <porterbox>  # e.g., arm64 porter box
# Build the package and verify reproducibility:
# (use reprotest or rebuild with same buildinfo)
```

## DEP-3 Header for Reproducibility Patches

```
Description: Make <package/tool> build reproducible on all architectures
Author: <Name> <email>
Forwarded: not-needed  # or link to upstream PR if applicable
Last-Update: YYYY-MM-DD
```

## Upstreaming

If the fix is in an upstream Makefile or build script (not Debian-specific):

1. **Submit to upstream** — Open a PR/PR against the upstream repository (e.g., iovisor/bcc for libbpf-tools)
2. **Reference the Debian bug** — Mention the reproduce.debian.net failure and architecture affected
3. **Keep the Debian patch** — Until upstream merges and a new release is available, keep the patch in `debian/patches/`
4. **Drop when upstream releases** — After importing new upstream version, check if the fix is included and drop the patch

## Related Tools

- `reprotest` — Test reproducibility locally by varying build environment
- `diffoscope` — Detailed binary comparison
- `strip-nondeterminism` — Post-process binaries to remove non-determinism (last resort)
- `disorderfs` — FUSE filesystem that randomizes directory iteration order

## References

- Debian Reproducible Builds: https://wiki.debian.org/ReproducibleBuilds
- reproduce.debian.net: https://reproduce.debian.net/
- diffoscope: https://diffoscope.org/
- SOURCE_DATE_EPOCH: https://reproducible-builds.org/specs/source-date-epoch/