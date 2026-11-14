# apt-listbugs Handling

## When It Triggers

- `apt-listbugs` checks Debian BTS for serious/critical bugs in packages being upgraded.
- On serious bug: halts upgrade with `Exiting with an error in order to stop the installation.`
- Output shows: `serious bugs of <pkg> (<old> -> <new>) <Outstanding>` and bug summary.

## Workarounds

### Override (accept bug temporarily)
```bash
sudo apt listbugs override <pkg>
sudo apt full-upgrade -y
```
- Allows upgrade to proceed despite the bug.
- Bug remains in BTS; override persists until bug is fixed or cleared.

### Hold Package
```bash
sudo apt-mark hold <pkg>
sudo apt full-upgrade -y
```
- Excludes package from upgrade.
- Remember to `apt-mark unhold <pkg>` later.

### Inspect Bug First
```bash
apt-listbugs show <pkg>
# or
apt-listbugs list <pkg>
```
- Shows bug numbers, severity, and summary.
- Decide if workaround is acceptable.

## Pitfalls

- Override affects all future upgrades of that package until bug is fixed.
- Holding packages can cause dependency conflicts over time.
- Critical bugs (higher than serious) cannot be overridden — must hold or fix.
- `apt-listbugs` only checks bugs at upgrade time; new bugs in already-installed versions are not caught.