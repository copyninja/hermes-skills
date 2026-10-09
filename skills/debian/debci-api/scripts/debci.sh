#!/usr/bin/env bash
# debci.sh — Helper script for debci/ci.debian.net API operations
# Uses gnome-keyring (via keyring Python lib) for API key retrieval.

set -euo pipefail

BASE_URL="https://ci.debian.net/api/v1"

# Retrieve API key from gnome-keyring, fallback to file
# Prints key to stdout (callers MUST use command substitution to capture it)
get_key() {
    python3 -c "import keyring; print(keyring.get_password('ci-debian-net', 'api-key'), end='')" 2>/dev/null && return
    # Fallback to file
    if [ -f ~/.secrets/.ci-debian-net.key ]; then
        cat ~/.secrets/.ci-debian-net.key
        return
    fi
    echo "ERROR: No API key found" >&2
    exit 1
}

# Validate API key (key is NOT printed to output)
auth() {
    local key
    key=$(get_key)
    local code user
    code=$(curl -s -o /dev/null -w "%{http_code}" -H "Auth-Key: $key" "$BASE_URL/auth")
    if [ "$code" = "200" ]; then
        user=$(curl -s -D - -o /dev/null -H "Auth-Key: $key" "$BASE_URL/auth" 2>/dev/null | grep -i 'Auth-User:' | sed 's/.*Auth-User: //;s/\r//')
        echo "OK — authenticated as: $user"
    else
        echo "FAIL — HTTP $code" >&2
        return 1
    fi
}

# Submit a test for a single package (key never leaves the script)
submit() {
    local suite="$1" arch="$2" package="$3"
    local priority="${4:-5}"
    local key
    key=$(get_key)
    curl -s -H "Auth-Key: $key" --data '' "$BASE_URL/test/$suite/$arch/$package" | python3 -m json.tool 2>/dev/null || curl -s -H "Auth-Key: $key" --data '' "$BASE_URL/test/$suite/$arch/$package"
}

# Submit a batch of tests (key never leaves the script)
submit_batch() {
    local suite="$1" arch="$2" tests_file="$3"
    local priority="${4:-5}"
    local key
    key=$(get_key)
    curl -s -H "Auth-Key: $key" \
        --data-urlencode "tests@${tests_file}" \
        --data "priority=$priority" \
        "$BASE_URL/test/batch" | python3 -m json.tool 2>/dev/null || curl -s -H "Auth-Key: $key" \
        --data-urlencode "tests@${tests_file}" \
        --data "priority=$priority" \
        "$BASE_URL/test/batch"
}

# Get test results since a timestamp (key never leaves the script)
results() {
    local since="$1"
    local key
    key=$(get_key)
    curl -s -H "Auth-Key: $key" "$BASE_URL/test?since=$since" | python3 -m json.tool 2>/dev/null || curl -s -H "Auth-Key: $key" "$BASE_URL/test?since=$since"
}

# Get latest results for a specific package (polling helper, key never leaves script)
package_results() {
    local package="$1"
    local key
    key=$(get_key)
    curl -s -H "Auth-Key: $key" "$BASE_URL/test?since=0" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data.get('results', []):
    pkg = r.get('package') or ''
    if pkg == '$package':
        status = r.get('status') or 'queued'
        print(f\"  {r.get('suite',''):12s} {r.get('arch',''):8s} {r.get('version',''):20s} {status:8s} run_id={r.get('run_id','')}\")
"
}

# Retry a test run (key never leaves the script)
retry() {
    local run_id="$1"
    local key
    key=$(get_key)
    curl -s -X POST -H "Auth-Key: $key" "$BASE_URL/retry/$run_id" | python3 -m json.tool 2>/dev/null || curl -s -X POST -H "Auth-Key: $key" "$BASE_URL/retry/$run_id"
}

# Publish private tests (key never leaves the script)
publish() {
    local run_ids="$1"
    local key
    key=$(get_key)
    curl -s -X POST -H "Auth-Key: $key" --data "run_ids=$run_ids" "$BASE_URL/test/publish" | python3 -m json.tool 2>/dev/null || curl -s -X POST -H "Auth-Key: $key" --data "run_ids=$run_ids" "$BASE_URL/test/publish"
}

# List packages (key never leaves the script)
list_packages() {
    local backend="${1:-}"
    local limit="${2:-50}"
    local key
    key=$(get_key)
    local url="$BASE_URL/packages"
    if [ -n "$backend" ]; then
        url="$url?backend=$backend"
    fi
    url="$url&limit=$limit"
    curl -s -H "Auth-Key: $key" "$url" | python3 -m json.tool 2>/dev/null || curl -s -H "Auth-Key: $key" "$url"
}

# Show reject list (key never leaves the script)
reject_list() {
    local key
    key=$(get_key)
    curl -s -H "Auth-Key: $key" "$BASE_URL/reject_list" | python3 -m json.tool 2>/dev/null || curl -s -H "Auth-Key: $key" "$BASE_URL/reject_list"
}

# Print usage
usage() {
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  auth                      Validate API key"
    echo "  submit <suite> <arch> <pkg> [priority]  Submit a test run"
    echo "  submit-batch <suite> <arch> <tests.json> [priority]  Batch submit"
    echo "  results <since_unix_ts>  Get test results since timestamp"
    echo "  pkg-results <package>    Show latest results for a package"
    echo "  retry <run_id>           Retry a test"
    echo "  publish <run_ids>        Publish private tests (comma-separated)"
    echo "  packages [backend] [limit]  List packages (optional backend filter, default limit 50)"
    echo "  reject                   Show reject list"
    echo ""
    echo "Examples:"
    echo "  $0 auth"
    echo "  $0 submit unstable amd64 bpfcc 8"
    echo "  $0 pkg-results bpfcc"
    echo "  $0 results 1700000000"
}

# Main
case "${1:-}" in
    auth)        auth "$(get_key)" ;;
    submit)      submit "$2" "$3" "$4" "${5:-5}" ;;
    submit-batch) submit_batch "$2" "$3" "$4" "${5:-5}" ;;
    results)     results "$2" ;;
    pkg-results) package_results "$2" ;;
    retry)       retry "$2" ;;
    publish)     publish "$2" ;;
    packages)    list_packages "${2:-}" "${3:-50}" ;;
    reject)      reject_list ;;
    *)           usage ;;
esac
