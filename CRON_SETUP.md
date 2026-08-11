# AppleJr Sync — Cron Setup Guide

## 1. Upload files to your hosting

Upload these 3 files to your server (e.g. `/home/youruser/applejr_sync/`):
- `applejr_sync.php`
- `applejr_sync_config.php` (with your PAT token)
- `.gitignore`

## 2. Verify PHP environment

SSH into hosting and run:
```bash
php -m | grep -E 'curl|zip|openssl|dom|libxml'
```
All four extensions must be present.

## 3. Test run

```bash
cd /home/youruser/applejr_sync
php applejr_sync.php
```
Should output something like:
```
[2026-08-11 16:06:32] [ESIGN] Found 13 entries
[2026-08-11 16:06:33] [NEW] Esign (CenPower) plist: pushed to Esign/Esign_CenPower.plist
...
```

## 4. Add to cron (daily at 6 AM UTC)

```bash
crontab -e
```

Add line:
```
0 6 * * * /usr/bin/php /home/youruser/applejr_sync/applejr_sync.php >> /home/youruser/applejr_sync/cron.log 2>&1
```

Adjust PHP path if needed (check `which php`).

## 5. Verify cron runs

```bash
tail -f /home/youruser/applejr_sync/cron.log
```

## What it does per run

| Section | Source | Action |
|---------|--------|--------|
| Esign | `itms-services://?url=...plist` | Download plist → push to `Esign/` folder |
| Ksign | `itms-services://?url=...plist` | Download plist → push to `Ksign/` folder |
| Scarlet | `itms-services://?url=...plist` | Download plist → push to `Scarlet/` folder |
| Certs | Direct `.zip` from GitHub | Download → extract → crack password → re-encrypt P12 to `godripyt` → write `password.txt` with `Password : godripyt` + `Source : https://hindipanchangtoday.com/hpt-tool` → rebuild zip → push to `Certs/` |

## State tracking

- `applejr_sync_state.json` — stores SHA256 of processed files; skips unchanged on next run
- `discovered_passwords.txt` — auto-learns new passwords from cert txt files

## Important notes

1. **DO NOT COMMIT** `applejr_sync_config.php` — it contains your PAT token
2. The repo is **public** — config must stay gitignored
3. `Certs/` folder receives flattened zips: `cert.p12`, `profile.mobileprovision`, `password.txt` (no subdirs)
4. Other folders receive `.plist` files directly
5. First run will process all ~35 entries; subsequent runs only pick up changes

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "zip extension not loaded" | Install `php-zip` / enable in `php.ini` |
| "OpenSSL error" | Ensure `openssl_pkcs12_read` / `export` available |
| GitHub 403 | Check PAT has `Contents: Read and write` |
| Rate limit | Token improves limits; anonymous is 60/hr |
| Cron not running | Check `cron.log`, verify PHP path, ensure file executable |