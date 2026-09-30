#!/bin/bash
# bpfcc experimental buildd + package tracker monitor
# Outputs a deterministic snapshot; changes wake the agent.

OUT=""

# 1. Buildd status for experimental (amd64)
STATUS=$(curl -s -m 30 "https://buildd.debian.org/status/package.php?p=bpfcc&suite=experimental&arch=amd64" 2>/dev/null | grep -oE '(build status|Build Status|building|built|failed|uploaded|queued|waiting|accepted|undeclared)' | head -5 | sort -u | tr '\n' '|')
OUT+="buildd-amd64:$STATUS|"

# 2. Buildd log URL (latest amd64 build)
LOGLINK=$(curl -s -m 30 "https://buildd.debian.org/status/package.php?p=bpfcc&suite=experimental&arch=amd64" 2>/dev/null | grep -oE 'href="[^"]*buildlog[^"]*amd64[^"]*"' | head -1 | sed 's/href="//;s/"$//')
OUT+="loglink:${LOGLINK}|"

# 3. Package tracker (experimental)
PT=$(curl -s -m 30 "https://tracker.debian.org/pkg/bpfcc" 2>/dev/null | grep -oiE '(experimental|uploaded|accepted|inserted|published|gone|removed)' | head -10 | sort -u | tr '\n' '|')
OUT+="pt:$PT"

echo "$OUT"
