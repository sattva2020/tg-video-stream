#!/usr/bin/env node
import { spawn, spawnSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const isWindows = process.platform === 'win32';
const npmCmd = isWindows ? 'npm.cmd' : 'npm';
const npxCmd = isWindows ? 'npx.cmd' : 'npx';
const frontendDir = path.resolve('frontend');
const managePreview = process.env.SKIP_PREVIEW === '1' ? false : true;
const useDevServer = process.env.USE_DEV_SERVER === '1';
const runPlaywright = process.env.SKIP_PLAYWRIGHT === '1' ? false : true;
const previewHost = process.env.AUTH_PREVIEW_HOST || '127.0.0.1';
const previewPort = Number(process.env.AUTH_PREVIEW_PORT || 4173);
const maxTtiMs = Number(process.env.MAX_TTI_MS || 2000);
const maxDeltaMs = Number(process.env.MAX_TTI_DELTA_MS || 100);
const runId = process.env.PERF_RUN_ID || process.env.GITHUB_RUN_ID || new Date().toISOString().replace(/[:.]/g, '-');
const logsRoot = path.resolve('.internal', 'frontend-logs', 'perf', runId);
const baselineUrl = process.env.AUTH_BASELINE_URL || `http://${previewHost}:${previewPort}/auth`;
const errorUrl = process.env.AUTH_ERROR_URL || `${baselineUrl}?perfError=conflict`;
const lighthouseTimeoutMs = Number(process.env.LIGHTHOUSE_TIMEOUT_MS || 120000);
const playwrightTestPath = process.env.AUTH_PLAYWRIGHT_TEST || 'tests/e2e/auth.spec.ts';
const playwrightProject = process.env.AUTH_PLAYWRIGHT_PROJECT || 'chromium';
const playwrightWorkers = process.env.AUTH_PLAYWRIGHT_WORKERS || '1';

const cleaners = [];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function waitForReady(url, timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url, { method: 'GET' });
      if (response.ok) {
        return;
      }
    } catch (error) {
      // retry
    }
    await sleep(1000);
  }
  throw new Error(`Preview server не отвечает по адресу ${url}`);
}

function runFrontendCommand(args, label) {
  const result = spawnSync(npmCmd, args, {
    cwd: frontendDir,
    stdio: 'inherit',
    shell: isWindows
  });
  if (result.status !== 0) {
    throw new Error(`${label} завершилась с кодом ${result.status ?? 'null'}`);
  }
}

function startPreviewServer() {
  const cmdArgs = useDevServer
    ? ['run', 'dev', '--', '--host', previewHost, '--port', String(previewPort)]
    : ['run', 'preview', '--', '--host', previewHost, '--port', String(previewPort)];
  const preview = spawn(npmCmd, cmdArgs, {
    cwd: frontendDir,
    stdio: 'inherit',
    shell: isWindows
  });
  cleaners.push(async () => {
    if (!preview.killed) {
      preview.kill();
    }
  });
}

function runPlaywrightScenario() {
  const args = [
    'run',
    'test:ui',
    '--',
    playwrightTestPath,
    `--project=${playwrightProject}`,
    `--workers=${playwrightWorkers}`,
    '--reporter=line'
  ];
  runFrontendCommand(args, 'Playwright сценарий auth-errors');
}

function runLighthouseCommand(targetUrl, label) {
  const reportBase = path.join(logsRoot, label);
  const args = [
    'lighthouse',
    targetUrl,
    '--form-factor=mobile',
    '--screenEmulation.mobile=true',
    '--throttling.cpuSlowdownMultiplier=4',
    '--throttling.rttMs=150',
    '--throttling.throughputKbps=1600',
    '--output=json',
    '--output=html',
    `--output-path=${reportBase}`,
    `--max-wait-for-load=${lighthouseTimeoutMs}`,
    '--quiet',
    '--chrome-flags=--headless=new --no-sandbox --disable-dev-shm-usage'
  ];
  const result = spawnSync(npxCmd, args, {
    stdio: 'inherit',
    cwd: process.cwd(),
    shell: isWindows
  });
  if (result.status !== 0) {
    throw new Error(`Lighthouse ${label} завершился с кодом ${result.status ?? 'null'}`);
  }
  return {
    label,
    reportBase,
    jsonPath: `${reportBase}.report.json`,
    htmlPath: `${reportBase}.report.html`
  };
}

async function collectMetrics(descriptor) {
  const raw = JSON.parse(await readFile(descriptor.jsonPath, 'utf-8'));
  const tti = raw?.audits?.interactive?.numericValue;
  if (typeof tti !== 'number') {
    throw new Error(`Lighthouse не вернул audit.interactive для ${descriptor.label}`);
  }
  const lcp = raw?.audits?.['largest-contentful-paint']?.numericValue ?? null;
  const ttfb = raw?.audits?.serverResponseTime?.numericValue ?? null;
  return {
    label: descriptor.label,
    url: descriptor.url,
    tti,
    lcp,
    ttfb,
    jsonPath: descriptor.jsonPath,
    htmlPath: descriptor.htmlPath
  };
}

async function run() {
  await mkdir(logsRoot, { recursive: true });

  if (managePreview) {
    if (!useDevServer) {
      runFrontendCommand(['run', 'build'], 'frontend build');
    }
    startPreviewServer();
    await waitForReady(baselineUrl);
  }

  const baselineDescriptor = runLighthouseCommand(baselineUrl, 'baseline');
  baselineDescriptor.url = baselineUrl;
  const baselineMetrics = await collectMetrics(baselineDescriptor);

  if (runPlaywright) {
    runPlaywrightScenario();
  }

  const errorDescriptor = runLighthouseCommand(errorUrl, 'error');
  errorDescriptor.url = errorUrl;
  const errorMetrics = await collectMetrics(errorDescriptor);

  const deltaMs = errorMetrics.tti - baselineMetrics.tti;
  const summary = {
    runId,
    timestamps: {
      baseline: new Date().toISOString(),
      error: new Date().toISOString()
    },
    baseline: baselineMetrics,
    error: errorMetrics,
    deltaMs,
    thresholds: {
      maxTtiMs,
      maxDeltaMs
    },
    urls: {
      baseline: baselineUrl,
      error: errorUrl
    }
  };

  await writeFile(path.join(logsRoot, 'summary.json'), JSON.stringify(summary, null, 2), 'utf8');
  await writeFile(
    path.join(logsRoot, 'summary.md'),
    `# Auth Error TTI Report\n\n- Run ID: ${runId}\n- Baseline TTI: ${baselineMetrics.tti.toFixed(2)} ms\n- Error TTI: ${errorMetrics.tti.toFixed(2)} ms\n- ΔTTI: ${deltaMs.toFixed(2)} ms (limit ${maxDeltaMs} ms)\n- Reports: ${path.relative(process.cwd(), baselineMetrics.htmlPath)}, ${path.relative(process.cwd(), errorMetrics.htmlPath)}\n`,
    'utf8'
  );

  if (baselineMetrics.tti > maxTtiMs) {
    throw new Error(`Baseline TTI ${baselineMetrics.tti} превышает лимит ${maxTtiMs}`);
  }
  if (errorMetrics.tti > maxTtiMs) {
    throw new Error(`Error TTI ${errorMetrics.tti} превышает лимит ${maxTtiMs}`);
  }
  if (deltaMs > maxDeltaMs) {
    throw new Error(`ΔTTI ${deltaMs} превышает лимит ${maxDeltaMs}`);
  }

  console.log(`TTI baseline=${baselineMetrics.tti.toFixed(2)} ms, error=${errorMetrics.tti.toFixed(2)} ms, Δ=${deltaMs.toFixed(2)} ms (OK)`);
}

run()
  .catch(async (error) => {
    console.error('[auth-error-tti] Ошибка:', error.message);
    await cleanup();
    process.exit(1);
  })
  .then(async () => {
    await cleanup();
  });

process.on('SIGINT', async () => {
  console.log('\n[auth-error-tti] Получен SIGINT, выполняем очистку...');
  await cleanup();
  process.exit(1);
});

async function cleanup() {
  while (cleaners.length) {
    const fn = cleaners.pop();
    try {
      await fn();
    } catch (error) {
      console.error('[auth-error-tti] Не удалось корректно завершить ресурс:', error.message);
    }
  }
}
