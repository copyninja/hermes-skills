---
title: debci-api
description: "debci/ci.debian.net API: submit and check CI test runs."
name: debci-api
version: 1.0.0
author: Vasudev Kamath
license: GPL-3.0
hermes:
  tags: [debian, ci, debci, autopkgtest, package-testing]
  related_skills: [autopkgtest]
---

## When to Use

Use this skill when you need to:
- Submit a package to debci for CI testing (any package, suite, or architecture)
- Check the status/results of debci test runs
- Retry failed tests or publish private tests
- List packages registered in debci or check the reject list
- Integrate debci API calls into monitoring or automation scripts

## When NOT to Use

- **The package has no autopkgtest in the target suite.** debci runs `autopkgtest` against the installed package. If the source package has no `Testsuite: autopkgtest` in `debian/control` for that suite, submitting to debci produces a useless result — the test runner has nothing to execute. Check `debian/control` first. If there is no ATE, add it (see `debian-autopkgtest`) before submitting to debci.
- **You want ad-hoc test results without API access.** For read-only checks (did a build pass?), the [debci web UI](https://ci.debian.net) or `getbuildlog` may be simpler.
- **You need to debug a test failure in detail.** debci API returns status and metadata, not full log output. Fetch build logs from buildd.debian.org for the actual test log.

Always use this skill when working with debci/ci.debian.net programmatically — even for seemingly simple tasks like checking if a test passed, since the API has pagination (`since`/`until`), private vs public test visibility, and specific auth requirements.

# debci API Skill

Interact with [Debian Continuous Integration (debci)](https://ci.debian.net) via its REST API.

## API Key

The API key is stored in **gnome-keyring** under service `ci-debian-net`, username `api-key`.

- **Store key:** `python3 -c "import keyring; keyring.set_password('ci-debian-net', 'api-key', '<YOUR_KEY>')"`
- **Key file fallback:** `~/.secrets/.ci-debian-net.key` (if keyring unavailable)

**The API key must never appear in command output, chat, or log files.** Always retrieve it programmatically via command substitution (`KEY=$(get_key)`) — never print it, echo it, or include it in a request that produces visible output. The helper script `scripts/debci.sh` enforces this: `get_key()` writes only to stdout for capture by `$(...)`, and every other function reads the key internally. If you call the API directly (not via the helper script), capture the key the same way — `KEY=$(python3 -c "import keyring; print(keyring.get_password('ci-debian-net', 'api-key'), end='')")` — and never print `$KEY` or pass it to any command that may leak it.

The key file `~/.secrets/.ci-debian-net.key` has the same constraint: read it into a variable, do not `cat` it to the terminal.

## Base URL

```
https://ci.debian.net/api/v1
```

All requests (except key management) must include the header:
```
Auth-Key: <api-key>
```

## Endpoints

### Auth / Key Validation

```bash
curl -s -o /dev/null -w "%{http_code}" -H "Auth-Key: $KEY" https://ci.debian.net/api/v1/auth
# 200 = valid, 403 = invalid
```

Also returns `Auth-User` header with the username.

### List Packages

```bash
curl -s -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/packages[?backend=<name>&limit=<N>]"
```

Returns JSON array of `{id, name, backend, removed, storage_limit}`. Optional filters:
- `?backend=<name>` — only packages with that backend
- `?backend=` — only packages with no backend

### Submit a Test

**Single package:**
```bash
curl -s -H "Auth-Key: $KEY" --data '' "https://ci.debian.net/api/v1/test/{suite}/{arch}/{package}"
```

**⚠️ Suite acceptance:** This debci instance only accepts `unstable` as a suite. Submitting any other suite (e.g. `experimental`, `testing`, `trixie`, `sid`) returns HTTP 403 with `{"error": "Invalid suite: <name>"}`. Always verify the suite is accepted before submitting — either by testing with a dry-run curl, or by checking existing test results for the target suite via `/api/v1/test?since=0` and inspecting the `suite` field of returned results.

**Batch submit:**
```bash
curl -s -H "Auth-Key: $KEY" \
  --data-urlencode "tests=@tests.json" \
  --data "priority=8" \
  "https://ci.debian.net/api/v1/test/batch"
```

Where `tests.json` is a JSON array:
```json
[
  {
    "package": "bpfcc",
    "trigger": "autopkgtest-check",
    "pin-packages": [["src:some-dep", "unstable"]],
    "is_private": false,
    "extra-apt-sources": ["experimental"]
  }
]
```

Parameters:
- `suite` — Debian suite (e.g. `unstable`, `testing`, `experimental`)
- `arch` — architecture (e.g. `amd64`, `arm64`)
- `priority` — integer 1–10 (optional)
- `is_private` — bool; private tests are only visible to the API key owner
- `pin-packages` — array of `[package_spec, suite]` pairs for pinning
- `extra-apt-sources` — array of extra apt source names
- `backend` — backend name (optional, uses server default if omitted)
- `autopkgtest` — autopkgtest variant name (optional)

**Shortcut endpoint** (single package, no JSON body needed):
```
POST /api/v1/test/{suite}/{arch}/{package}
```

### Get Test Results

```bash
curl -s -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/test?since=<unix_ts>"
```

Mandatory `since` parameter (UNIX timestamp). Returns:
```json
{
  "until": <latest_timestamp>,
  "results": [
    {
      "trigger": "...",
      "package": "...",
      "arch": "...",
      "suite": "...",
      "version": "...",
      "status": "pass" | "fail" | "tmpfail" | null,
      "run_id": 12345,
      "is_private": false,
      "extra_apt_sources": [],
      "updated_at": "...",
      "date": "...",
      "duration_seconds": 123
    }
  ]
}
```

**Important:** `since` should use the `until` value from the previous response to avoid duplicates. A running test will have `status: null` and gets updated when completed.

### Retry a Test

```bash
curl -s -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/retry/{run_id}"
# or POST to retry
curl -s -X POST -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/retry/{run_id}"
```

### Publish Private Tests

```bash
curl -s -X POST -H "Auth-Key: $KEY" \
  --data "run_ids=123,456" \
  "https://ci.debian.net/api/v1/test/publish"
```

### Reject List

```bash
curl -s -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/reject_list"
```

Returns packages blocked from testing, structured as:
```json
{
  "package": {
    "suite": {
      "arch": {
        "version": ""
      }
    }
  }
}
```

## Helper Script

A reusable shell script is provided at `scripts/debci.sh` for common operations. All functions read the API key internally — it never appears in output.

## Scope discipline

When a task involves debci, prefer **monitoring** over manual checking when either is viable:

- **Set up a cron monitor** for ongoing status changes (e.g. buildd picking up a new version, test status flipping from `fail` to `pass`).
- **Check once manually** only when you need an answer now and monitoring is overkill.
- **Do not submit test runs as "verification"** unless the package actually has ATE in the target suite — submissions for packages without ATE are wasted debci slots and produce no useful result. Check `debian/control` for `Testsuite: autopkgtest` before submitting.

## Example Workflow: Check bpfcc test status

Use the helper script — it handles key retrieval internally:

```bash
# 1. Validate key
bash scripts/debci.sh auth

# 2. Check existing results for a package
bash scripts/debci.sh pkg-results bpfcc

# 3. Submit a new test
bash scripts/debci.sh submit unstable amd64 bpfcc 8

# 4. List all packages
bash scripts/debci.sh packages 2>/dev/null | head -20
```

Or call the API directly — key is always captured via command substitution, never printed:

```bash
KEY=$(python3 -c "import keyring; print(keyring.get_password('ci-debian-net', 'api-key'), end='')")
curl -s -o /dev/null -w "%{http_code}\n" -H "Auth-Key: $KEY" https://ci.debian.net/api/v1/auth
```

## Notes

- Only test requests made by the same API key are returned by `/api/v1/test`.
- debci is licensed under GPLv3+; source at [salsa.debian.org/ci-team/debci](https://salsa.debian.org/ci-team/debci).
- API docs generated 2026-09-19.
