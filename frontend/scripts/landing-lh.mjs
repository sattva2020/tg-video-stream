#!/usr/bin/env node
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { setTimeout as delay } from 'node:timers/promises';
import lighthouse from 'lighthouse';
import { launch } from 'chrome-launcher';

const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const defaultUrl = 'http://127.0.0.1:4173/';
const targetUrl = process.env.LH_URL ?? defaultUrl;
const shouldBuild = process.env.LH_SKIP_BUILD !== 'true';
const shouldSpawnPreview = process.env.LH_SKIP_PREVIEW !== 'true';
const parsedTarget = new URL(targetUrl);
const previewPort = parsedTarget.port || '4173';
const previewHost = parsedTarget.hostname;
const timeoutMs = Number(process.env.LH_SERVER_TIMEOUT ?? 60000);

const runCommand = (cmd, args = []) =>
  new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: 'inherit', shell: false });
    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${cmd} ${args.join(' ')} exited with code ${code}`));
      }
    });
    child.on('error', reject);
  });

const waitForServer = async (url, deadlineMs) => {
  const deadline = Date.now() + deadlineMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { method: 'HEAD' });
      if (response.ok) {
        return;
      }
    } catch {
      // server not ready yet
    }
    await delay(1000);
  }
  throw new Error(`Timed out waiting for ${url}`);
};

let previewProcess;
let chrome;

try {
  if (shouldBuild) {
    console.log('[landing-lh] Building frontend bundle...');
    await runCommand(npmCmd, ['run', 'build']);
  }

  if (shouldSpawnPreview) {
    console.log('[landing-lh] Starting vite preview on port %s', previewPort);
    previewProcess = spawn(
      npmCmd,
      ['run', 'preview', '--', '--host', previewHost, '--port', previewPort.toString(), '--strictPort'],
      { stdio: 'inherit', shell: false },
    );
    await waitForServer(targetUrl, timeoutMs);
  }

  chrome = await launch({ chromeFlags: ['--headless=new', '--no-sandbox'] });
  const runnerResult = await lighthouse(
    targetUrl,
    {
      port: chrome.port,
      output: ['json', 'html'],
      logLevel: 'info',
      disableStorageReset: true,
      onlyCategories: ['performance', 'accessibility'],
    },
  );

  const lhr = runnerResult.lhr;
  const reports = Array.isArray(runnerResult.report) ? runnerResult.report : [runnerResult.report];
  const [jsonReport, htmlReport] = reports;

  const outputDir = path.resolve(process.cwd(), '..', '.internal', 'lighthouse');
  fs.mkdirSync(outputDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const jsonPath = path.join(outputDir, `landing-${timestamp}.json`);
  const htmlPath = path.join(outputDir, `landing-${timestamp}.html`);
  fs.writeFileSync(jsonPath, jsonReport);
  if (htmlReport) {
    fs.writeFileSync(htmlPath, htmlReport);
  }

  const perfScore = Math.round((lhr.categories.performance?.score ?? 0) * 100);
  const ttiSeconds = ((lhr.audits.interactive?.numericValue ?? 0) / 1000).toFixed(2);
  console.log('[landing-lh] Performance=%s, TTI=%ss, reports saved to %s', perfScore, ttiSeconds, outputDir);
} catch (error) {
  console.error('[landing-lh] Failed:', error);
  process.exitCode = 1;
} finally {
  if (chrome) {
    await chrome.kill();
  }
  if (previewProcess && !previewProcess.killed) {
    previewProcess.kill('SIGINT');
  }
}
