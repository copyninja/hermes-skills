#!/usr/bin/env python3
"""debci-logs-for-run.py — resolve the log suite from the debci API for any run_id, then fetch + summarize.

Usage:
    debci-logs-for-run.py <run_id> [package]

Example:
    debci-logs-for-run.py 76489375

Behavior:
    1. Queries /api/v1/test?since=0 for a result whose run_id matches.
    2. Reads suite, arch, package, version from the result.
    3. Builds the log URL and downloads + summarizes it via
       debci-fetch-log.py's fetch_and_summarize().

Exit codes:
    0 = log summarized
    1 = run not found, no results, download failed, decompression error
    2 = usage error
"""

import gzip
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def api_key():
    r = subprocess.run(
        ["python3", "-c", "import keyring; print(keyring.get_password('ci-debian-net', 'api-key'), end='')"],
        capture_output=True, text=True, check=True)
    return r.stdout.strip()


def results_since(since=0):
    url = f"https://ci.debian.net/api/v1/test?since={since}"
    r = subprocess.run(
        ["curl", "-s", "-H", f"Auth-Key: {api_key()}", url],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("curl failed on /api/v1/test")
    try:
        return json.loads(r.stdout)
    except Exception as e:
        raise RuntimeError(f"bad JSON from API: {e}")


def find_run(run_id):
    for res in results_since(0).get("results", []):
        if str(res.get("run_id")) == str(run_id):
            return res
    return None


def determine_suite(run):
    suite = run.get("suite")
    if not suite:
        raise RuntimeError(f"run {run_id} has no 'suite' field in API result")
    arch = run.get("arch")
    package = run.get("package")
    return suite, arch, package, run.get("version")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    run_id = sys.argv[1]
    package = sys.argv[2] if len(sys.argv) > 2 else None

    res = find_run(run_id)
    if res is None:
        print(f"ERROR: run {run_id} not found in /api/v1/test results")
        sys.exit(1)

    suite, arch, package, version = determine_suite(res)
    print(f"# resolved run {run_id}:")
    print(f"#   suite      = {suite}")
    print(f"#   arch       = {arch}")
    print(f"#   package    = {package or 'bpfcc'}")
    print(f"#   version    = {version}")
    print(f"#   status     = {res.get('status')}")

    # Reuse debci-fetch-log.py's fetch+summarize.
    import subprocess as sp
    script = os.path.join(HERE, "debci-fetch-log.py")
    cmd = ["python3", script, suite, arch, run_id] + ([package] if package else [])
    proc = sp.run(cmd, capture_output=True, text=True)
    print(proc.stdout, end="")
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
