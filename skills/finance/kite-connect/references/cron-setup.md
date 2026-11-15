# Cron / Timer Setup for Daily Token Expiry Reminder

## Option 1: systemd Timer (Recommended)

### Service Unit
```ini
# ~/.config/systemd/user/kite-token-reminder.service
[Unit]
Description=Kite Connect token expiry reminder
After=network-online.target

[Service]
Type=oneshot
ExecStart=/home/vasudev/.hermes/bin/hermes run kite-connect:token-expiry-reminder
# Or direct script:
# ExecStart=/home/vasudev/devel/hermes-skills/skills/finance/kite-connect/scripts/kite_auth.py status
Environment=PATH=/home/vasudev/.local/bin:/usr/bin:/bin
```

### Timer Unit
```ini
# ~/.config/systemd/user/kite-token-reminder.timer
[Unit]
Description=Daily 6:05 AM token expiry check

[Timer]
OnCalendar=*-*-* 06:05:00
Persistent=true
RandomizedDelaySec=30

[Install]
WantedBy=timers.target
```

### Enable
```bash
systemctl --user daemon-reload
systemctl --user enable --now kite-token-reminder.timer
systemctl --user status kite-token-reminder.timer
```

## Option 2: crontab

```bash
# Edit crontab
crontab -e

# Add:
5 6 * * * /home/vasudev/devel/hermes-skills/skills/finance/kite-connect/scripts/kite_auth.py status 2>&1 | logger -t kite-token
```

## Option 3: Hermes Cron Job

If using Hermes' built-in cron:

```yaml
# ~/.hermes/cron/kite-token-reminder.yaml
name: kite-token-reminder
schedule: "5 6 * * *"
command: "kite-connect:token-expiry-check"
platform: telegram
chat_id: "-5507172510"  # Home group
```

## Telegram Notification Format

The skill's `token-expiry-reminder` tool should send:

```
🔔 Kite Connect token expired at 06:00 IST
Run `kite-auth` to re-authenticate for today's session.
```

## Manual Test

```bash
# Test the reminder script
/home/vasudev/devel/hermes-skills/skills/finance/kite-connect/scripts/kite_auth.py status

# Expected output when expired:
# 🔴 Token EXPIRED at 2026-11-15 06:00

# Expected output when valid:
# 🟢 Token valid: 14h 32m remaining (expires 2026-11-16 06:00)
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Timer not firing | `systemctl --user status kite-token-reminder.timer`; check `journalctl --user -u kite-token-reminder` |
| No Telegram notification | Verify `chat_id` and Hermes bot permissions in group |
| Token not actually expired | Check system clock (`timedatectl`); NTP sync required |