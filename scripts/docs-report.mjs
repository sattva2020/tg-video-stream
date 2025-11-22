import { promises as fs } from 'fs';
import path from 'path';

const rootDir = process.cwd();
const docTargets = [
  'README.md',
  'docs',
  path.join('specs', '001-modern-home-design'),
];

const outDir = path.join('.internal', 'docs');

async function listMarkdownFiles(targetPath) {
  const absolute = path.isAbsolute(targetPath)
    ? targetPath
    : path.join(rootDir, targetPath);
  const stats = await fs.stat(absolute).catch(() => null);
  if (!stats) {
    return [];
  }
  if (stats.isFile()) {
    if (absolute.toLowerCase().endsWith('.md')) {
      return [absolute];
    }
    return [];
  }
  const entries = await fs.readdir(absolute);
  const results = await Promise.all(
    entries.map(async (entry) =>
      listMarkdownFiles(path.join(absolute, entry))
    )
  );
  return results.flat();
}

async function collectDocs() {
  const files = (
    await Promise.all(docTargets.map((target) => listMarkdownFiles(target)))
  )
    .flat()
    .sort();
  const payload = [];
  for (const file of files) {
    const content = await fs.readFile(file, 'utf8');
    const relative = path.relative(rootDir, file).replace(/\\/g, '/');
    const words = content
      .split(/\s+/)
      .filter(Boolean)
      .length;
    payload.push({ file: relative, bytes: content.length, words });
  }
  return payload;
}

async function ensureOutputDir() {
  await fs.mkdir(outDir, { recursive: true });
}

async function main() {
  await ensureOutputDir();
  const payload = await collectDocs();
  const summary = {
    generatedAt: new Date().toISOString(),
    fileCount: payload.length,
    totalWords: payload.reduce((sum, item) => sum + item.words, 0),
    files: payload,
  };
  const filename = `docs-report-${Date.now()}.json`;
  const reportPath = path.join(outDir, filename);
  await fs.writeFile(reportPath, JSON.stringify(summary, null, 2), 'utf8');
  console.log(`Доклады сохранены в ${reportPath}`);
}

main().catch((error) => {
  console.error('[docs-report] Ошибка генерации отчёта');
  console.error(error);
  process.exitCode = 1;
});
