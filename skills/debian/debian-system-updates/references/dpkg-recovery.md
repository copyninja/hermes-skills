# dpkg Interruption Recovery

## Symptoms

- `E: dpkg was interrupted, you must manually run 'sudo dpkg --configure -a'`
- `dpkg --audit` shows packages in `Half-Installed` or `Half-Configured` state.
- Lock files exist: `/var/lib/dpkg/lock`, `/var/lib/dpkg/lock-frontend`.

## Recovery Steps

1. **Check for active dpkg/apt processes**
   ```bash
   ps aux | grep -E '(apt|dpkg)' | grep -v grep
   lsof /var/lib/dpkg/lock /var/lib/apt/lists/lock /var/cache/apt/archives/lock
   ```
   - If no process holds locks, they are stale.

2. **Run dpkg configure**
   ```bash
   sudo dpkg --configure -a
   ```
   - Requires TTY for sudo password if NOPASSWD not set.
   - User must run this in their own terminal.

3. **Resume upgrade**
   ```bash
   DEBIAN_FRONTEND=noninteractive sudo apt full-upgrade -y
   ```

4. **Verify**
   ```bash
   dpkg --audit
   apt list --upgradable
   ```

## Pitfalls

- Running `sudo dpkg --configure -a` from Hermes terminal fails if sudo needs TTY.
  Instruct user to run it manually.
- Stale lock files are harmless if no process holds them; dpkg will overwrite.
- Partial installs may leave packages in `Unpacked` state; `--configure -a` completes them.