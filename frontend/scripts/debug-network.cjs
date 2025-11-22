const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const base = process.env.BASE_URL || 'http://localhost:3000';
  const url = base + '/login';
  console.log('[netdebug] opening', url);
  await page.goto(url, { waitUntil: 'domcontentloaded' });

  const events = [];
  page.on('request', req => events.push({ type: 'request', method: req.method(), url: req.url() }));
  page.on('response', res => events.push({ type: 'response', status: res.status(), url: res.url() }));

  // fill using placeholders/names
  await page.locator('input[name="username"], input[name="email"], input[placeholder*="Email"], input[placeholder*="Электрон"]').first().fill('admin@sattva.com');
  await page.locator('input[name="password"], input[placeholder*="Пароль"]').first().fill('Zxy1234567');

  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  const outDir = path.join(process.cwd(), '.internal', 'playwright-mcp', 'debug');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'network-log.json'), JSON.stringify(events, null, 2));
  console.log('[netdebug] saved to', outDir);

  await page.screenshot({ path: path.join(outDir, 'login-post-submit.png'), fullPage: true });
  await browser.close();
})();
