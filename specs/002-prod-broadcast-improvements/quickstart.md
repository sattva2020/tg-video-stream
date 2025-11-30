## Quickstart: Session regen and deploy notes

This quickstart covers the most common operational tasks for the Production Broadcast Improvements feature: regenerating a Telegram session string and pushing `.env` to a host, and enabling scheduled `yt-dlp` updates.

1) Regenerate SESSION_STRING (interactive)

 - On the machine where you will run the service (local or remote), ensure Python 3.12 and project venv are available.
 - Run the interactive helper:

```bash
python test/auto_session_runner.py --regenerate pyrogram
```

 - Follow prompts: enter phone number, confirmation code, and (if needed) 2FA password. The helper will write a session to memory; with `--write-env` (if implemented) it can save masked `SESSION_STRING` into local `.env`.

2) Push `.env` to remote (optional)

 - Use the helper to push:

```bash
python test/auto_session_runner.py --remote-user root --remote-host 10.99.99.2 --remote-path /opt/tg_video_streamer/current/.env
```

 - Or manually copy with scp and ensure ownership/permissions (on remote):

```bash
scp .env root@10.99.99.2:/opt/tg_video_streamer/current/.env
ssh root@10.99.99.2 'chown tgstream:tgstream /opt/tg_video_streamer/current/.env && chmod 600 /opt/tg_video_streamer/current/.env && sudo systemctl restart tg_video_streamer'
```

3) Enable yt-dlp auto-update (on remote)

 - Copy the `yt-dlp-update.service` and `yt-dlp-update.timer` from `specs/002-prod-broadcast-improvements/deploy/systemd/` to `/etc/systemd/system/` and enable the timer:

```bash
sudo cp specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now yt-dlp-update.timer
```

Logs for the updater are written to `/var/log/yt-dlp-update.log`.

4) Notes

 - Keep `.env` secure (chmod 600) and owner `tgstream`.
 - CI deploy steps (see `.github/workflows/snippets/restart-tg_video_streamer-step.yml`) can be used to restart the service after updating releases.
