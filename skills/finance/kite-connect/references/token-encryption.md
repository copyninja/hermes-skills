# Token Encryption

## Design

- **Algorithm**: Fernet (AES-128-GCM + HMAC-SHA256)
- **Key Derivation**: SHA-256(`api_secret` + `machine-id`)
- **Payload**: JSON `{access_token, expiry}`

## Why This Approach

| Concern | Solution |
|---------|----------|
| `api_secret` in config | Stored in keyring (`secret-tool`) or `.env` (gitignored) |
| Token at rest | Encrypted with machine-bound key |
| Key rotation | Re-run `kite-auth` → new token, new encryption |
| Cross-device | Each device has unique `machine-id` → separate tokens |

## Key Derivation Details

```python
machine_id = Path("/etc/machine-id").read_text().strip()  # stable per install
seed = (api_secret + machine_id).encode()
key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
```

- `/etc/machine-id` is created at OS install, stable across reboots
- If missing, falls back to `"fallback"` (still binds to `api_secret`)
- `api_secret` never written to disk in plaintext

## Storage

```
~/.local/share/kite-connect/token.enc  # 0600 permissions
~/.config/kite-connect/config.toml     # api_key only (api_secret in keyring)
```

## Keyring Setup (Recommended)

```bash
# Store api_secret in GNOME Keyring
secret-tool store --label=kite-connect api_secret "your_api_secret_here"

# Verify
secret-tool lookup label kite-connect
```

## Config Template

```toml
# ~/.config/kite-connect/config.toml
api_key = "your_api_key"
api_secret = ""  # leave empty if using keyring
redirect_url = "http://localhost:8765/kite/callback"
token_file = "~/.local/share/kite-connect/token.enc"
callback_port = 8765
```

## Security Notes

- Token file is **machine-bound** — copying to another machine won't decrypt
- `api_secret` only used server-side for checksum; never in browser
- Local callback server binds to `127.0.0.1` only
- No network exposure of secrets