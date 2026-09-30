# Reading the QA Developer Page

## When to Use

Read the QA developer page to get a one-glance summary of a package's health: RC bug count, buildd status across arches, FTBFS state, experimental build status, and whether a newer upstream version is available.

URL: `https://qa.debian.org/developer.php?login=<logname>&comaint=yes`

## Columns and what they mean

| Column | What to read |
|---|---|
| Package name + `[U]` / `[M]` | `[U]` = co-maintained (you're a comaint), `[M]` = maintainer. Click through to tracker. |
| Bug count (e.g. `10`) | Total bugs against the source package. Click for breakdown. |
| RC count (the next column, e.g. `1`) | Release-critical bugs (critical/grave/serious). This is the number that blocks release. |
| Buildd state | `✓` = installed on all required arches. `✘` = failed on that arch. `∿` = build attempted. Multiple arches listed. |
| Experimental | Shown when the package has an experimental version. Check each arch — all-failed experimental builds often indicate a build environment regression. |
| Lintian | `✔` = no errors. |
| Piuparts | `Passed` / `Failed` in testing/unstable/experimental. |
| Reproducible builds | `FTBFS` = fails to build from source (red). `GOOD` = reproducible. |
| Popcon | Popularity contest score — rough install base. |
| Watch | If `behind`, a newer upstream version exists (e.g. `0.37.0` when packaged is `0.35.0`). |

## FTBFS in experimental

When experimental builds fail across ALL architectures since the same date, that is usually a build environment issue (toolchain update, missing dependency, spec change) rather than an architecture-specific bug. Check:

1. When did it start? (the date column)
2. Was there a toolchain or dependency change around that date?
3. Does the same version build in unstable? (if yes, the problem is experimental-specific)

## RC bug vs FTBFS distinction

An RC bug is a runtime/policy defect reported against the package. FTBFS is a build failure. They can share a root cause but are tracked separately in BTS. Don't assume fixing one fixes the other — check both.

## Excuses page

`/cgi-bin/excuses.php?package=<pkg>` — Shows whether the package has RT (release team) excuses for RC bugs. If a package has RC bugs with no excuse, it may be delayed from testing.