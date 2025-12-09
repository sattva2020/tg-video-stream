# Troubleshooting & Known Issues

## Server Migration & CPU Compatibility

### `py-tgcalls` and `SIGILL` (Illegal Instruction)

When migrating to a new server (especially older hardware or specific VPS configurations), you might encounter a `SIGILL` error causing the streamer service to crash immediately upon starting playback.

**Symptoms:**
- Service starts but crashes when trying to play audio/video.
- Logs show `code=killed, status=4/ILL`.
- `journalctl` shows "Illegal instruction".

**Cause:**
The `ntgcalls` binary (a dependency of `py-tgcalls`) is often compiled with AVX/AVX2 instructions. If the target server's CPU does not support these instructions, the process will crash.

**Solution:**
You may need to downgrade or pin specific versions of `py-tgcalls` that use a more compatible build of `ntgcalls`.

**Verified Configuration (as of Dec 2025):**
- `py-tgcalls==2.2.1` (uses `ntgcalls>=2.0.1`)
- `pyrogram==2.0.106`

**Note:** Newer versions of `py-tgcalls` (e.g., 2.2.8) might require newer `pyrogram` versions or have stricter CPU requirements. Always check `lscpu` on the new server.
