export default async ({ page }: { page: any }) => {
  console.log('[mcp] launching example smoke');
  await page.goto('https://example.com', { waitUntil: 'domcontentloaded' });
  const title = await page.title();
  console.log(`[mcp] title: ${title}`);
  await page.context().browser()?.close();
};