const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on('console', msg => console.log('PAGE LOG:', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err));

  await page.goto('http://localhost:3000/register', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  console.log('HTML length', (await page.content()).length);
  await page.screenshot({ path: 'debug_register.png', fullPage: true });
  console.log('screenshot saved to debug_register.png');
  await browser.close();
})();
