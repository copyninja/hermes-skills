#!/bin/bash
# Snapshot script template for debian-package-monitoring
# Output deterministic pipe-separated key:value pairs
# No timestamps, no random order

OUT=""
# 1. Pool version
POOL_VER=$(curl -sL -m 30 "https://ftp.debian.org/debian/dists/unstable/main/binary-amd64/Packages.gz" 2>/dev/null | gunzip -c 2>/dev/null | awk '/^Package: bpfcc$/{f=1} f && /^Version:/{print $2; exit}')
OUT+="ft-version:${POOL_VER}|"

# 2. Buildd status
BUILDD=$(curl -sL -m 30 "https://buildd.debian.org/status/package.php?p=bpfcc&suite=unstable&arch=amd64" 2>/dev/null | grep -oE '<td[^>]*class="status [^"]+"[^>]*>[^<]*</td>' | head -1 | sed 's/<[^>]*>//g' | xargs)
OUT+="buildd-amd64:${BUILDD}|"

# 3. Debci latest for version
KEY=$(python3 -c "import keyring; print(keyring.get_password('ci-debian-net', 'api-key'), end='')" 2>/dev/null)
DEBCI=$(curl -sL -m 30 -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/test?since=0" 2>/dev/null | python3 -c "
import sys, json
try:
    d=json.load(sys.stdin)
    for r in reversed(d.get('results',[])):
        if r.get('package')=='bpfcc' and r.get('suite')=='unstable':
            print(f\"{r.get('version')}:{r.get('status')}:{r.get('run_id')}\")
            break
except: pass
")
OUT+="debci:${DEBCI}"

echo "$OUT"
