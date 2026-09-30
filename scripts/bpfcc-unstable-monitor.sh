#!/bin/bash
# bpfcc unstable monitor — tracks 0.37.0+ds-3 acceptance + buildd + debci
# Snapshot fields:
#   ft-version:  version in unstable pool for bpfcc
#   ft-tools:    version in unstable pool for bpfcc-tools
#   buildd-amd64: buildd status for unstable/amd64
#   buildd-arm64: buildd status for unstable/arm64
#   debci:       latest debci result for bpfcc unstable (version:status:run_id)
#   debci-ttl:   total debci results for bpfcc in unstable

OUT=""

# 1. Version in unstable pool for bpfcc
POOL_VER=$(curl -sL -m 30 "https://ftp.debian.org/debian/dists/unstable/main/binary-amd64/Packages.gz" 2>/dev/null | gunzip -c 2>/dev/null | awk '/^Package: bpfcc$/{f=1} f && /^Version:/{print $2; exit}')
OUT+="ft-version:${POOL_VER}|"

# 2. Version for bpfcc-tools (confirms upload completeness)
FT_TOOLS=$(curl -sL -m 30 "https://ftp.debian.org/debian/dists/unstable/main/binary-amd64/Packages.gz" 2>/dev/null | gunzip -c 2>/dev/null | awk '/^Package: bpfcc-tools$/{f=1} f && /^Version:/{print $2; exit}')
OUT+="ft-tools:${FT_TOOLS}|"

# 3. Buildd unstable amd64 status
BUILDD=$(curl -sL -m 30 "https://buildd.debian.org/status/package.php?p=bpfcc&suite=unstable&arch=amd64" 2>/dev/null | grep -oE '<td[^>]*class="status [^"]+"[^>]*>[^<]*</td>' | head -1 | sed 's/<[^>]*>//g' | xargs)
OUT+="buildd-amd64:${BUILDD}|"

# 4. Buildd unstable arm64 status
BUILDD_ARM64=$(curl -sL -m 30 "https://buildd.debian.org/status/package.php?p=bpfcc&suite=unstable&arch=arm64" 2>/dev/null | grep -oE '<td[^>]*class="status [^"]+"[^>]*>[^<]*</td>' | head -1 | sed 's/<[^>]*>//g' | xargs)
OUT+="buildd-arm64:${BUILDD_ARM64}|"

# 5. Debci latest bpfcc unstable result
KEY=$(python3 -c "import keyring; print(keyring.get_password('ci-debian-net', 'api-key'), end='')" 2>/dev/null)
DEBCI=$(curl -sL -m 30 -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/test?since=0" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    for r in reversed(d.get('results',[])):
        if (r.get('package') or '') == 'bpfcc' and r.get('suite') == 'unstable':
            print(f\"{r.get('version')}:{r.get('status')}:{r.get('run_id')}\")
            break
except: pass
" 2>/dev/null)
OUT+="debci:${DEBCI}|"

# 6. Total debci results for bpfcc unstable (for context)
DEBCI_TTL=$(curl -sL -m 30 -H "Auth-Key: $KEY" "https://ci.debian.net/api/v1/test?since=0" 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    results = [r for r in d.get('results',[]) if (r.get('package') or '')=='bpfcc' and r.get('suite')=='unstable']
    print(len(results))
except:
    print('error')
" 2>/dev/null)
OUT+="debci-ttl:${DEBCI_TTL}"

echo "$OUT"
