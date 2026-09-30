# BTS Query Patterns

## When to Use

Dig into specific bug numbers, filter by severity or tag, or decide whether a bug is still active vs resolved.

## Source package bug list

```
https://bugs.debian.org/cgi-bin/pkgreport.cgi?src=<source-package>
```

Pages are HTML — curl + grep for severity markers (`critical`, `grave`, `serious`, `important`) and bug numbers.

## RC filter

Append to the source package URL:

```
&sev-inc=critical&sev-inc=grave&sev-inc=serious
```

This shows only bugs at or above serious severity.

## Individual bug

```
https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=<number>
```

Look for:
- `Severity:` line
- `Tags:` line (patch, security, ftbfs, moreinfo, wishlist, etc.)
- `Forwarded:` line (none / pending / yes / no)
- `Found in version:` — which package version exposed the bug
- Last modified date — stale bugs may need a nudge

## Bug status vocabulary

| Status | Meaning |
|---|---|
| New / unclassified | Reported, not yet triaged |
| Found | Confirmed present in a specific version |
| Fixed | Resolved in a version (check which) |
| Done | Closed |
| Pending | Waiting on upstream or external action |

## Searching by package

- Source package: `src:bpfcc`
- Binary package: `bpfcc-tools`, `libbpf-tools`, `python3-bpfcc`, etc.
- The BTS `pkgreport.cgi?src=` page lists all binary packages in that source.

## Useful query params

- `archive=no` — hide archived bugs
- `pend-exc=pending-fixed` — exclude pending-fixed
- `collapse=1` — collapse duplicate reports
- `users=all` — show all user-tagged bugs
- `versions=package` — version-specific view