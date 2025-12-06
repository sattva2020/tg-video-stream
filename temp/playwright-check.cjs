const path = require('path');
const { chromium } = require(path.resolve(__dirname, '../frontend/node_modules/playwright'));
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('console', msg => console.log('CONSOLE', msg.type(), msg.text()));
  page.on('pageerror', err => console.error('PAGE_ERROR', err));
  await page.goto('https://sattva-streamer.top', { waitUntil: 'networkidle' });
  const hero = await page.textContent('[data-landing-hero]');
  const navText = await page.textContent('header');
  console.log('HERO_TEXT', hero.replace(/\s+/g, ' ').trim());
  console.log('HEADER_TEXT', navText.replace(/\s+/g, ' ').trim());
  await browser.close();
})();
