# Static Binary Install Recipe

Download a static binary from an upstream release, extract it, and install it
into the user `bin` directory.

## Steps

1. Identify the OS and architecture (`uname -m`).
2. Determine the release URL (typically `https://dl.<project>.com/stable/` or
   GitHub releases).
3. Download the tarball and extract it into `$HOME/.local/bin`.
4. Verify the binary: `<pkg> --version`.
5. Add `$HOME/.local/bin` to `PATH` if it is not already present.

## Notes

- Static binaries do not link against system libraries, so they run on any
  compatible OS/arch.
- The daemon (if any) may still need root for device access (e.g. TAP/TUN).
- Prefer the distro package when available.
