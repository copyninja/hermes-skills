# Planning autopkgtest for a Debian package

## When to Use

When the user asks to add autopkgtest (ATE) to a Debian source package — i.e. create `debian/tests/` with a `control` file and test scripts that validate the installed package post-install. Use before delegating implementation to an agent (e.g. agy with Claude Sonnet).

## What autopkgtest is (quick orientation)

autopkgtest (ATE) runs tests **against the installed package**, not the build tree. It is orthogonal to `dh_auto_test` (build-time tests). Key implications:

- **`debian/rules` `DEB_BUILD_MAINT_OPTIONS=nocheck` is irrelevant to ATE.** That flag only suppresses `dh_auto_test` at build time. ATE scripts run after `dpkg -i` on the built `.deb`s.
- **`debian/tests/control` declares test dependencies** via `Depends: @` (the package under test) plus anything else needed (e.g. `python3-bpfcc`, `bpftool`).
- **Test scripts must be executable** (`chmod +x`) shell scripts (or other interpreters declared in the script header).
- **The test runs in a testbed** (schroot, qemu, lxc, or the local machine) where the package is installed from the built artifacts.

## Planning workflow

### 1. Survey the upstream test suite

Before writing any ATE script, understand what the upstream project tests:

```bash
cd ~/Documents/Debian/<pkgname>
# List upstream test files
find tests/ src/python/tests/ -name "*.py" -o -name "*.cc" -o -name "*.sh" 2>/dev/null
# Read each test file's imports to determine root requirements
head -30 tests/python/<test>.py
```

Look for:
- Imports that require root: `attach_kprobe`, `attach_uprobe`, `perf_event_open`, `pyroute2.NetNS`, `BPF.attach_*`
- Imports that need special filesystem: `/sys/kernel/debug/` (debugfs), `/proc/sys/`
- Pure computational tests: disassembly, encoding, data structure manipulation — these can run unprivileged

### 2. Classify each test by privilege requirement

| Category | How to spot | ATE treatment |
|---|---|---|
| Pure computation (no kernel, no root) | No `attach_*`, no `pyroute2.NetNS`, no `/sys/kernel/debug` access | Run unprivileged in ATE |
| Needs root (kprobes, perf, network namespaces) | `attach_kprobe`, `BPF.attach_*`, `pyroute2`, `NetNS` | `Restrictions: needs-root` — skip on unprivileged runners |
| Needs debugfs | Accesses `/sys/kernel/debug/bpf/` or similar | May need `Restrictions: needs-root` + debugfs mounted |
| Needs network | Sends packets, opens raw sockets | May need `Restrictions: needs-root` or a network-capable testbed |

### 3. Decide what to include in the initial autopkgtest

**Rule: start with the unprivileged subset.** Root-required tests are a future extension, not part of the initial implementation. A minimal ATE that passes on any Debian desktop is more valuable than a comprehensive one that only runs on dedicated testbeds.

For each unprivileged test, ask:
- Does it validate something meaningful about the installed package? (import succeeds, basic API works, critical utilities function)
- Is it self-contained or does it depend on other test helpers? (e.g. `simulation.py` is a helper for network namespace tests — not needed for smoke tests)

### 4. Decide how to ship test files with the package

ATE scripts run against the **installed package**, not the source tree. Upstream test files live in the source at `tests/python/`, but ATE scripts run in a testbed with only installed files.

**Rule: do not run upstream unit tests via ATE.** ATE is for packaging tests (import succeeds, paths correct, dependencies satisfied). Upstream tests belong to build-time `dh_auto_test`, not ATE. Inline a minimal smoke test that exercises the installed package's public API — import checks, utility calls, basic API exercise with no kernel attachment.

For a minimal smoke test, **inline the test in the ATE shell script** — embed a Python heredoc. This avoids shipping files and keeps the scope to packaging validation.

**Avoid:** shipping upstream test files via `debian/<pkg>.docs` solely for ATE, and running `test_disassembler.py` or other upstream tests from ATE. That mixes upstream correctness testing with packaging testing.

### 5. Write the plan document before implementation

Before delegating to an agent, write a plan document that covers:

- **Branch name** — e.g. `deploy/autopkgtest`
- **Files to create** — each `debian/tests/*.` script, `debian/tests/control`, any `.docs`/`.install` additions
- **Files to modify** — `debian/control` (add `Testsuite: autopkgtest`), `debian/changelog`
- **Files to NOT touch** — explicitly call out `debian/rules` (no change needed for ATE) and any files the agent might be tempted to modify
- **Classification of upstream tests** — which are in scope (unprivileged), which are future work (root), which are out of scope
- **Local verification command** — how to build and run the ATE locally after implementation
- **Risks and mitigations** — known constraints (no passwordless sudo, missing debugfs, etc.)

Save the plan under `~/.hermes/cache/scratch/<topic>/` (not the home directory or the package source tree).

### 6. Hand off to the implementation agent

Use `agy` (not `delegate_task`) for implementation that edits files in the local repository:

```bash
agy --model claude-sonnet --print-file ~/.hermes/cache/scratch/<topic>/plan.md
```

Or run interactively:
```bash
agy --model claude-sonnet --prompt-interactive
```

Specify:
- The branch to work on (`deploy/autopkgtest`)
- The plan document path
- That changes must be safe (edits to `debian/` only, no destructive operations)
- The local verification command to run after implementation

### 7. Local verification after implementation

```bash
cd ~/Documents/Debian/<pkgname>
# Build
DEBEMAIL=$(git config user.email) DEBNAME=$(git config user.name) \
  gbp buildpackage --git-builder=sbuild -s --source-only-changes -d unstable --git-ignore-new

# Run ATE using the built packages
sudo autopkgtest ../<pkg>_*.deb -- schroot sid-amd64
```

If no schroot is available, do a manual smoke test:
```bash
sudo apt install ./<pkg>_*.deb ./libbpfcc_*.deb ./python3-bpfcc_*.deb
python3 -c "from bcc import BPF; print('OK')"
```

## Pitfalls

- **Don't confuse ATE with build-time tests.** `dh_auto_test` runs during `dpkg-buildpackage`; ATE runs against the installed `.deb`. Disabling `nocheck` in `debian/rules` does nothing for ATE.
- **ATE tests the installed package, not the source tree. Do not run upstream unit tests via ATE.** Upstream unit tests (e.g. `test_disassembler.py`) belong to build-time `dh_auto_test`, not ATE. ATE's purpose is packaging validation (import succeeds, paths correct, dependencies satisfied). Inline a minimal smoke test that exercises the installed package's public API — import checks, utility calls, basic API exercise with no kernel attachment — instead of shipping or running upstream test files.
- **Don't assume upstream test files are accessible at ATE runtime.** They live in the source tree, not the installed package.
- **Don't put ATE scripts in `debian/tests/` and expect them to find upstream tests by relative path.** The working directory at ATE runtime is the testbed root, not the source tree.
- **Don't mark all tests as `needs-root`.** Start with unprivileged tests; root tests are a future extension. A package with only `needs-root` ATE provides no coverage on standard desktop runners.
- **Don't inline massive test code.** Inline only minimal smoke tests.
- **Don't forget to make scripts executable.** `chmod +x debian/tests/*` — ATE skips non-executable files in `debian/tests/`.
- **Do NOT tag before the upload is accepted** (see main SKILL.md pitfall). This applies to the autopkgtest upload too.
- **Runtime kernel UAPI headers are often missing in minimal testbeds.** Packages that compile BPF programs at runtime (libbpfcc, libbpf-tools, any bcc-based package) depend on `/usr/include/linux/bpf.h` and friends at test time. These headers come from `linux-libc-dev` (userspace UAPI headers), NOT `linux-headers-$(uname -r)` (kernel-version-specific module headers). Add `linux-libc-dev` to each test stanza's `Depends:` so the testbed has the headers installed. Add a smoke-test check for `/usr/include/linux/bpf.h` and fail with a clear message if it is missing — this catches the packaging gap rather than silently failing inside the BPF loader.
- **`--help` is a valid smoke test for root-requiring CLI tools.** Tools that attach eBPF programs (kprobes, tracepoints, etc.) need root to actually function, but running `--help` exercises library linking and BPF program compilation without attachment. Use it in unprivileged ATE smoke tests to validate the installed binary exists and can initialize its BPF subsystem. Accept exit codes 0 or 1 (some tools print usage to stderr and exit 1 for `--help`); treat other exit codes as failures.
- **Inline the smoke test; do not ship upstream test files for ATE.** Embedding a Python heredoc in the shell script keeps scope to packaging validation (import, basic API, CLI presence). Shipping upstream test files via `debian/<pkg>.docs` solely to run them from ATE mixes upstream correctness testing with packaging testing — that belongs in build-time `dh_auto_test`.

## Handing off to an implementation agent

Use `agy` for local file edits (not `delegate_task`, which cannot modify the working tree):

```bash
agy --model claude-sonnet --print-timeout=600s \
    --print "$(cat /home/vasudev/.hermes/cache/scratch/<topic>/plan.md)" \
    --dangerously-skip-permissions
```

Or run interactively and paste the plan. In either case:
- Point the agent at the plan document and tell it to read the **entire** plan before starting.
- Specify the branch (`deploy/autopkgtest` from `master`).
- List the exact files to create/modify AND the files to NOT touch (e.g. `debian/rules`, upstream test files).
- Include the verification command so the agent can self-check before reporting back.
- Tell the agent to stop and report failure if the build or ATE run fails — do not push on failure.
