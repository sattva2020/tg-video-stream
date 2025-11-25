/* eslint-env node */
import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

const DEFAULT_URL = process.env.LH_AUTH_URL || 'http://localhost:5173/auth';
const DEFAULT_PRESET = 'desktop';
const DEFAULT_OUTPUT = './logs/lighthouse-auth-report.html';
const MOBILE_OUTPUT = './logs/lighthouse-auth-mobile.html';
const CHROME_FLAGS = process.env.LH_CHROME_FLAGS || '--headless --disable-gpu';

const { options, extras } = parseArgs(process.argv.slice(2));

const requestedPreset = options.get('preset') || DEFAULT_PRESET;
const targetUrl = options.get('url') || DEFAULT_URL;
const outputPath = options.get('output-path') || (requestedPreset === 'mobile' ? MOBILE_OUTPUT : DEFAULT_OUTPUT);
const chromeFlags = options.get('chrome-flags') || CHROME_FLAGS;
const startPreview = options.get('start-preview') !== 'false';
const previewPort = options.get('preview-port') || new URL(targetUrl).port || '4173';

const extraCliArgs = [];

if (options.has('form-factor')) {
  extraCliArgs.push(`--form-factor=${options.get('form-factor')}`);
}

const lighthouseArgs = [
  targetUrl,
  '--output',
  'html',
  '--output-path',
  outputPath,
  '--quiet',
  `--chrome-flags=${chromeFlags}`,
];

if (requestedPreset === 'mobile') {
  lighthouseArgs.push('--preset=desktop');
  if (!options.has('form-factor')) {
    lighthouseArgs.push('--form-factor=mobile');
  }
  if (!options.has('screenEmulation.mobile')) {
    lighthouseArgs.push('--screenEmulation.mobile=true');
  }
} else {
  lighthouseArgs.push(`--preset=${requestedPreset}`);
  if (!options.has('form-factor')) {
    lighthouseArgs.push(`--form-factor=${requestedPreset === 'desktop' ? 'desktop' : 'mobile'}`);
  }
}

lighthouseArgs.push(...extraCliArgs, ...extras);

mkdirSync(path.dirname(outputPath), { recursive: true });

const previewProcess = startPreview ? launchPreview(previewPort) : null;

if (previewProcess) {
  await waitForServer(targetUrl, 30000);
}

const result = spawnSync('npx', ['-y', 'lighthouse', ...lighthouseArgs], {
  stdio: 'inherit',
  shell: true,
});

if (previewProcess) {
  previewProcess.kill();
}

if (result.status !== 0) {
  process.exit(result.status ?? 1);
}

function launchPreview(port) {
  const child = spawn('npm', ['run', 'preview', '--', '--port', port], {
    stdio: 'inherit',
    shell: true,
  });
  return child;
}

async function waitForServer(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  const healthUrl = new URL(url);
  healthUrl.pathname = '/';

  while (Date.now() < deadline) {
    try {
      const response = await fetch(healthUrl);
      if (response.ok || response.status >= 200) {
        return;
      }
    } catch {
      // Ignore connection errors until server becomes available.
    }
    await delay(1000);
  }

  throw new Error(`Preview server at ${healthUrl.origin} not reachable`);
}

function parseArgs(argv) {
  const options = new Map();
  const extras = [];

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) {
      extras.push(token);
      continue;
    }

    const [rawKey, inlineValue] = token.split('=');
    const key = rawKey.replace(/^--/, '');

    if (inlineValue !== undefined) {
      options.set(key, inlineValue);
      continue;
    }

    const next = argv[i + 1];
    if (next && !next.startsWith('--')) {
      options.set(key, next);
      i += 1;
    } else {
      options.set(key, 'true');
    }
  }

  return { options, extras };
}
