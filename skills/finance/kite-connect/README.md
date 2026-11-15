# Kite Connect Skill for Hermes Agent

Read-only portfolio/margin access for Zerodha Kite Connect v3 API.

## Quick Start

### 1. Create Kite Connect App
1. Go to https://developers.kite.trade/login
2. Create app → get `api_key` and `api_secret`
3. Set **Redirect URL**: `http://localhost:8765/kite/callback`

### 2. Configure
```bash
mkdir -p ~/.config/kite-connect
cat > ~/.config/kite-connect/config.toml <<'EOF'
api_key = "your_api_key_here"
api_secret = ""  # leave empty to use keyring
redirect_url = "http://localhost:8765/kite/callback"
token_file = "~/.local/share/kite-connect/token.enc"
callback_port = 8765
EOF
```

### 3. Store Secret in Keyring (Recommended)
```bash
secret-tool store --label=kite-connect api_secret "your_api_secret_here"
```

### 4. Daily Auth (Run Each Morning)
```bash
python -m scripts.kite_auth auth
# Opens browser → login with 2FA → saves token valid until 6 AM next day
```

### 5. Query Portfolio
```bash
python -m scripts.kite_auth holdings   # Long-term holdings
python -m scripts.kite_auth positions  # Derivatives/intraday positions
python -m scripts.kite_auth margins    # Funds & margin
python -m scripts.kite_auth profile    # User profile
python -m scripts.kite_auth status     # Token expiry check
```

## Automation

### systemd Timer (6:05 AM reminder)
```bash
# ~/.config/systemd/user/kite-token-reminder.timer
[Timer]
OnCalendar=*-*-* 06:05:00
Persistent=true

# Enable:
systemctl --user enable --now kite-token-reminder.timer
```

### Hermes Cron
Add to `~/.hermes/cron/kite-token-reminder.yaml`:
```yaml
name: kite-token-reminder
schedule: "5 6 * * *"
command: "kite-connect:token-expiry-check"
platform: telegram
chat_id: "-5507172510"
```

## Security

- `api_secret` in GNOME Keyring (not config file)
- `access_token` encrypted at rest (Fernet, machine-bound key)
- Local callback server binds to `127.0.0.1` only
- No secrets in browser / redirect URL

## Files

| Path | Purpose |
|------|---------|
| `scripts/kite_auth.py` | Main CLI: auth + all read endpoints |
| `references/kite-api.md` | API endpoint details |
| `references/token-encryption.md` | Encryption design |
| `references/cron-setup.md` | Timer/cron configuration |
| `pyproject.toml` | Python dependencies |

## Requirements

- Python 3.10+
- `httpx`, `cryptography`, `tomli`, `tomli-w`
- `secretstorage` (optional, for keyring)
- GNOME Keyring or compatible secret service

## License

MIT