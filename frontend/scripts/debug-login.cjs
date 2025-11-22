const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const base = process.env.BASE_URL || 'http://localhost:3000';
  const url = base + '/login';
  console.log('[debug] opening', url);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 20000 }).catch(e => console.error('goto error', e.message));
  const html = await page.content();
  const outDir = path.join(process.cwd(), '.internal', 'playwright-mcp', 'debug');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'login.html'), html);
  await page.screenshot({ path: path.join(outDir, 'login.png'), fullPage: true });
  console.log('[debug] saved html and screenshot to', outDir);
  await browser.close();
})();
