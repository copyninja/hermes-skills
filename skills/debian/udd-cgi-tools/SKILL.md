---
name: udd-cgi-tools
category: debian
description: Query UDD CGI for RC bugs, FTBFS, patches, dashboards.
---

# UDD CGI Tools

Tools to fetch and parse data from UDD's CGI scripts at https://udd.debian.org/cgi-bin/

## Available Queries

| CGI Script | Purpose | Output Format |
|------------|---------|---------------|
| `bugs.cgi` | RC bugs for a suite (testing/unstable) | HTML table |
| `bugs-with-patches.cgi` | Bugs with patches ready for review | Plain text (package,url,bug#) |
| `ftbfs.cgi` / `ftbfs-bugs.json.cgi` | FTBFS packages by arch/release | HTML form + results / JSON |
| `bug-blockers.cgi` | Bugs blocking transitions | HTML |
| `autoremovals.cgi` | Packages slated for autoremoval | Plain text |
| `wnpp-checks.cgi` | WNPP (orphaned/RFA/ITA) packages | HTML |
| `sponsorstats.cgi` | Sponsorship statistics | HTML |
| `ddpo-bugs.cgi` | Bugs for a maintainer/team | Plain text |
| `nobugs.cgi` | Packages with zero bugs | HTML |
| `dmd.cgi` | Debian Maintainer Dashboard | HTML (JS) |

## CLI Usage

```bash
# RC bugs for testing suite
udd rc-bugs forky --limit 20
udd rc-bugs trixie --key-only --json

# Bugs with patches for your packages
udd patches bpfcc smartctl-exporter

# FTBFS on specific architecture
udd ftbfs --arch amd64 --release trixie --limit 10
udd ftbfs --arch ppc64el --release sid

# Maintainer dashboard (DDPO summary)
udd dashboard vasudev@debian.org --rc-only --limit 20

# Autoremoval candidates
udd autoremovals --limit 20

# WNPP (orphaned/RFA/ITA) packages
udd wnpp --limit 20
```

## Python Usage

```python
from udd_cgi import UDDClient, get_rc_bugs, get_patches_for_packages, get_ftbfs, get_maintainer_summary

client = UDDClient()

# RC bugs
bugs = client.rc_bugs("forky")

# Bugs with patches
patches = client.bugs_with_packages(["bpfcc", "smartctl-exporter"])

# FTBFS
ftbfs = client.ftbfs("amd64", "trixie")

# Maintainer summary
summary = client.maintainer_summary("vasudev@debian.org")
rc_pkgs = [e for e in summary if e.rc > 0]
```

## Implementation Notes

- All endpoints are public, no auth required
- HTML parsing via BeautifulSoup (fallback to regex)
- JSON endpoints preferred where available
- Rate-limit: be respectful (cache results, don't hammer)
- UDD updates every ~2 days; CGI data reflects that latency

## Key URLs

- Base: `https://udd.debian.org/cgi-bin/`
- Bugs search: `https://udd.debian.org/bugs.cgi`
- Schema: `https://udd.debian.org/schema/udd.html`
- Source: `https://salsa.debian.org/qa/udd`
- Dumps: `https://udd.debian.org/dumps/udd.dump` (1.9 GB, every 2 days)

## Files

- `scripts/udd_cgi.py` — Main client module (importable)
- `scripts/udd` — Unified CLI (subcommands: rc-bugs, patches, ftbfs, dashboard, autoremovals, wnpp)
- `scripts/udd-rc-bugs` — CLI: RC bugs for suite
- `scripts/udd-patches` — CLI: bugs with patches for packages
- `scripts/udd-ftbfs` — CLI: FTBFS query
- `scripts/udd-dashboard` — CLI: maintainer dashboard (DDPO summary)
- `scripts/udd-autoremovals` — CLI: autoremoval candidates
- `scripts/udd-wnpp` — CLI: WNPP packages

## Pitfalls

- **RC bugs endpoint is `/bugs.cgi` at BASE_UDD (`https://udd.debian.org/bugs.cgi`), NOT `/cgi-bin/rcblog.cgi`** — the latter is a summary page with historical week-by-week data, not the actual bug list.
- **FTBFS JSON endpoint returns a list of bug objects directly, not a dict with a `results` key** — parse as `data` (list), not `data.get("results", [])`.
- **DDPO maintainer summary (`ddpo-bugs.cgi`) returns plain text** with format `pkg:total(rc) done(rc) pending(rc) forwarded(rc)` — skip lines starting with `(?)` which are summary totals.
- **FTBFS JSON bug objects use `source` field for package name**, not `package`; fallback to `affected_sources[0]` if missing.
- **`bugs-with-patches.cgi` returns CSV: `package,url,bug#`** — simple split on comma works.
- **All endpoints are public but rate-limit** — UDD updates every ~2 days; cache results locally when possible.
- **Symlink setup**: The skill lives in `~/devel/hermes-skills/skills/debian/udd-cgi-tools/` and is symlinked to `~/.hermes/skills/debian/udd-cgi-tools/` for Hermes profile discovery. Ensure the target directory exists before creating the symlink.
