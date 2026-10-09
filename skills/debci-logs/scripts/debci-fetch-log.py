#!/usr/bin/env python3
"""debci-fetch-log.py — deterministic fetch + summary of a Debian CI (debci) test log.

Usage:
    debci-fetch-log.py <suite> <arch> <run_id> [package]

Arguments:
    suite     debci log-suite name (e.g. "testing" or "unstable")
    arch      debian architecture (s390x, amd64, arm64, ...)
    run_id    the autopkgtest run id from the debci API results
    package   source package name (default "bpfcc")

Behavior (deterministic):
    1. Builds the unambiguous URL:
           https://ci.debian.net/data/autopkgtest/<suite>/<arch>/b/<pkg>/<run_id>/log.gz
    2. Downloads it with an Auth-Key request to the ci.debian.net API.
    3. Decompresses the gzipped autopkgtest log.
    4. Prints a clean, stable summary: per-test [PASS|FAIL|SKIP], plus
       the testbed release and a final "ALL/SOME tests passed" line.

Exit codes:
    0 = log downloaded and summarized
    1 = download failed (HTTP != 200) or decompression error
    2 = usage error

Log-suite note:
    Debian CI (ci.debian.net) reports the bpfcc results under suite "unstable"
    in /api/v1/test, but the autopkgest logs live under the run's actual suite
    (currently "testing"). Pass the suite seen in the API results; the script
    does not guess it.
"""

import gzip
import os
import re
import subprocess
import sys

HOME = os.path.expanduser("~")

def get_key():
    # Retrieve API key from gnome-keyring (mirrors debci-api SKILL.md convention)
    r = subprocess.run(
        ["python3", "-c",
         "import keyring; print(keyring.get_password('ci-debian-net','api-key'), end='')"],
        capture_output=True, text=True, check=True)
    return r.stdout.strip()

def fetch_log(suite, arch, run_id, package="bpfcc"):
    url = f"https://ci.debian.net/data/autopkgtest/{suite}/{arch}/b/{package}/{run_id}/log.gz"
    key = get_key()
    proc = subprocess.run(
        ["curl", "-s", "-H", f"Auth-Key: {key}", "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True)
    if proc.returncode != 0 or len(proc.stdout) < 200:
        return None, f"download failed (HTTP {proc.returncode}, {len(proc.stdout)} bytes)", None
    try:
        text = gzip.decompress(proc.stdout).decode("utf-8", "replace")
    except Exception as e:
        return None, f"decompression error: {e}", None
    return text, None, proc.stdout

def summarize(text):
    results = []
    all_passed = False
    for raw in text.splitlines():
        s = raw.strip()
        # final per-test result line: "<n>s <testname>  PASS|FAIL  <detail>"
        m = re.match(r"^\S+s\s+(\S+)\s+(PASS|FAIL|SKIP)\s+(.*)$", s)
        if m:
            results.append({"test": m.group(1), "status": m.group(2), "detail": m.group(3)})
            continue
        # overall summary line: "ALL SMOKE TESTS PASSED" or "X tests passed, Y failed"
        if s == "ALL SMOKE TESTS PASSED":
            all_passed = True
            results.append({"test": "OVERALL", "status": "PASS", "detail": "smoke tests passed"})
            continue
        if re.match(r"^\d+ tests? (passed|failed) \(", s):
            all_passed = "passed" in s
            results.append({"test": "OVERALL", "status": "PASS" if "passed" in s else "FAIL",
                            "detail": s.split("(", 1)[0].strip()})
    # Deduplicate: keep last occurrence of each test name.
    seen, dedup = set(), []
    for r in reversed(results):
        if r["test"] in seen:
            continue
        seen.add(r["test"])
        dedup.append(r)
    dedup.reverse()
    return dedup, all_passed

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(2)
    suite, arch, run_id = sys.argv[1], sys.argv[2], sys.argv[3]
    package = sys.argv[4] if len(sys.argv) > 4 else "bpfcc"

    text, err, raw = fetch_log(suite, arch, run_id, package)
    if err:
        print(f"ERROR: {err}")
        print("Fetch URL used: {scheme}://{host}{path}".format(
            scheme="https", host="ci.debian.net",
            path=f"/data/autopkgtest/{suite}/{arch}/b/{package}/{run_id}/log.gz"))
        sys.exit(1)

    res, all_passed = summarize(text)
    print(f"# {suite}/{arch} bpfcc run {run_id}")
    print(f"# downloaded {len(text)} bytes (gzip compressed)")
    print(f"# overall_passed={all_passed}")
    passed = sum(1 for r in res if r["status"] == "PASS")
    failed = sum(1 for r in res if r["status"] == "FAIL")
    skipped = sum(1 for r in res if r["status"] == "SKIP")
    for r in res:
        print(f"  [{r['status']:>4}] {r['test']}  {r['detail']}")
    print(f"# summary: {passed} pass, {failed} fail, {skipped} skip (total {len(res)})")
    sys.exit(0)

if __name__ == "__main__":
    main()
