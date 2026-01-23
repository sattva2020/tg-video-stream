#!/usr/bin/env node
/*
  dev-keepalive.js
  ----------------
  Simple watcher script to ensure the frontend dev server (Vite) is restarted
  automatically if it exits unexpectedly during local development.

  Usage: node scripts/dev-keepalive.js

  Behavior:
   - Spawns `npm run dev -- --host 0.0.0.0` to ensure Vite binds to all interfaces
   - Pipes stdout/stderr to `frontend/logs/vite.log` and `frontend/logs/vite.err`
   - Restarts process after a short delay if it exits with non-zero code
    - Pipes stdout/stderr to `.internal/frontend-logs/vite.log` and `.internal/frontend-logs/vite.err`
   - Exits cleanly on SIGINT/SIGTERM (ctrl+c)
*/

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Resolve robustly for Windows + posix paths. We want repo root.
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..', '..');
const logsDir = path.join(ROOT, 'frontend', 'logs');
if (!fs.existsSync(logsDir)) fs.mkdirSync(logsDir, { recursive: true });

const outLog = fs.createWriteStream(path.join(logsDir, 'vite.log'), { flags: 'a' });
const errLog = fs.createWriteStream(path.join(logsDir, 'vite.err'), { flags: 'a' });

function timestamp() {
  return new Date().toISOString();
}

let child = null;
let restarting = false;

function startDev() {
  if (restarting) return;
  const cmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
  const runCmd = `${cmd} run dev -- --host 0.0.0.0`;
  console.log(`${timestamp()} - Starting Vite dev server: ${runCmd}`);

  // Use shell true for better compatibility on Windows + Git Bash
  child = spawn(runCmd, {
    cwd: path.join(ROOT, 'frontend'),
    env: process.env,
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: true
  });

  // pipe to console + logs
  child.stdout.on('data', (chunk) => {
    const s = `${timestamp()} | STDOUT | ${chunk.toString()}`;
    process.stdout.write(s);
    outLog.write(s);
  });

  child.stderr.on('data', (chunk) => {
    const s = `${timestamp()} | STDERR | ${chunk.toString()}`;
    process.stderr.write(s);
    errLog.write(s);
  });

  child.on('exit', (code, sig) => {
    const msg = `${timestamp()} - Vite exited with code=${code} signal=${sig}`;
    console.log(msg);
    outLog.write(msg + '\n');
    errLog.write(msg + '\n');

    // Restart on non-zero exit code
    if (code !== 0) {
      restarting = true;
      console.log(`${timestamp()} - Restarting Vite in 2s...`);
      setTimeout(() => {
        restarting = false;
        startDev();
      }, 2000);
    } else {
      // normal exit — close logs and exit
      outLog.end();
      errLog.end();
      process.exit(code || 0);
    }
  });
}

process.on('SIGINT', () => {
  console.log('\nReceived SIGINT - killing vite process and exiting');
  if (child && !child.killed) child.kill('SIGINT');
  outLog.end();
  errLog.end();
  process.exit(0);
});

startDev();
