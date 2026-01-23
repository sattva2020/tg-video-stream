#!/usr/bin/env node
/*
  validate-chunks.js
  ------------------
  Analyzes frontend bundle chunks to detect oversized bundles and validate
  performance budgets. Used in CI/CD pipeline to catch bundle size regressions.

  Usage: node frontend/scripts/validate-chunks.js [options]

  Options:
    --threshold <kb>    Size threshold in KB (default: 500)
    --json              Output results in JSON format
    --verbose           Show detailed chunk breakdown
    --fail-on-warning   Exit with error code if warnings found
    --help              Show this help message

  Exit Codes:
    0: All chunks within threshold
    1: Errors or warnings (with --fail-on-warning)
*/

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..', '..');
const DIST_DIR = path.join(ROOT, 'frontend', 'dist');
const ASSETS_DIR = path.join(DIST_DIR, 'assets');

// Default threshold matches vite.config.ts chunkSizeWarningLimit
const DEFAULT_THRESHOLD_KB = 500;

/**
 * Parse command line arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    threshold: DEFAULT_THRESHOLD_KB,
    json: false,
    verbose: false,
    failOnWarning: false,
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    switch (arg) {
      case '--help':
      case '-h':
        options.help = true;
        break;
      case '--threshold':
      case '-t':
        options.threshold = parseInt(args[++i], 10);
        break;
      case '--json':
      case '-j':
        options.json = true;
        break;
      case '--verbose':
      case '-v':
        options.verbose = true;
        break;
      case '--fail-on-warning':
        options.failOnWarning = true;
        break;
      default:
        if (arg.startsWith('-')) {
          console.error(`Unknown option: ${arg}`);
          options.help = true;
        }
    }
  }

  return options;
}

/**
 * Display help message
 */
function showHelp() {
  console.log(`
Chunk Validation Script
=======================

Analyzes frontend bundle chunks to detect oversized bundles and validate
performance budgets.

Usage:
  node frontend/scripts/validate-chunks.js [options]

Options:
  --threshold, -t <kb>    Size threshold in KB (default: 500)
  --json, -j              Output results in JSON format
  --verbose, -v           Show detailed chunk breakdown
  --fail-on-warning       Exit with error code if warnings found
  --help, -h              Show this help message

Exit Codes:
  0: All chunks within threshold
  1: Errors or warnings (with --fail-on-warning)

Examples:
  node frontend/scripts/validate-chunks.js
  node frontend/scripts/validate-chunks.js --threshold 300 --verbose
  node frontend/scripts/validate-chunks.js --json --fail-on-warning
`);
}

/**
 * Get all JavaScript chunk files from the assets directory
 */
function getChunkFiles() {
  if (!fs.existsSync(ASSETS_DIR)) {
    throw new Error(
      `Assets directory not found: ${ASSETS_DIR}\n` +
      'Please build the frontend first: npm run build'
    );
  }

  const files = fs.readdirSync(ASSETS_DIR);
  return files
    .filter((file) => file.endsWith('.js') && !file.endsWith('.js.map'))
    .map((file) => {
      const filePath = path.join(ASSETS_DIR, file);
      const stats = fs.statSync(filePath);
      return {
        name: file,
        path: filePath,
        sizeBytes: stats.size,
        sizeKB: stats.size / 1024,
      };
    });
}

/**
 * Categorize chunk by type based on naming pattern
 */
function categorizeChunk(fileName) {
  const name = fileName.toLowerCase();

  if (name.includes('index-') || name.includes('main-')) {
    return 'entry';
  }
  if (name.includes('vendor') || name.includes('react-vendor') || name.includes('ui-vendor')) {
    return 'vendor';
  }
  if (name.includes('pages-')) {
    return 'page';
  }
  if (name.includes('components-')) {
    return 'component';
  }

  return 'chunk';
}

/**
 * Analyze chunks and detect oversized ones
 */
function analyzeChunks(chunks, threshold) {
  const analysis = {
    total: chunks.length,
    totalSizeBytes: 0,
    totalSizeKB: 0,
    byCategory: {
      entry: { count: 0, sizeKB: 0 },
      vendor: { count: 0, sizeKB: 0 },
      page: { count: 0, sizeKB: 0 },
      component: { count: 0, sizeKB: 0 },
      chunk: { count: 0, sizeKB: 0 },
    },
    oversized: [],
    warnings: [],
    details: [],
  };

  for (const chunk of chunks) {
    const category = categorizeChunk(chunk.name);

    // Update totals
    analysis.totalSizeBytes += chunk.sizeBytes;
    analysis.totalSizeKB += chunk.sizeKB;
    analysis.byCategory[category].count++;
    analysis.byCategory[category].sizeKB += chunk.sizeKB;

    // Check if oversized
    const isOversized = chunk.sizeKB > threshold;
    if (isOversized) {
      analysis.oversized.push({
        name: chunk.name,
        sizeKB: Math.round(chunk.sizeKB * 100) / 100,
        category,
        overBy: Math.round((chunk.sizeKB - threshold) * 100) / 100,
      });
      analysis.warnings.push(
        `${chunk.name} (${category}): ${Math.round(chunk.sizeKB)} KB exceeds threshold by ${Math.round(chunk.sizeKB - threshold)} KB`
      );
    }

    // Add detail
    analysis.details.push({
      name: chunk.name,
      sizeKB: Math.round(chunk.sizeKB * 100) / 100,
      category,
      status: isOversized ? 'oversized' : 'ok',
    });
  }

  // Round total
  analysis.totalSizeKB = Math.round(analysis.totalSizeKB * 100) / 100;

  return analysis;
}

/**
 * Format size for display
 */
function formatSize(kb) {
  if (kb < 1024) {
    return `${Math.round(kb)} KB`;
  }
  return `${(kb / 1024).toFixed(2)} MB`;
}

/**
 * Print analysis results in human-readable format
 */
function printResults(analysis, threshold, verbose) {
  console.log('\n╔════════════════════════════════════════════════════════════╗');
  console.log('║          Frontend Bundle Chunk Validation Report         ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');

  // Summary
  console.log('Summary:');
  console.log(`  Total Chunks:    ${analysis.total}`);
  console.log(`  Total Bundle:    ${formatSize(analysis.totalSizeKB)}`);
  console.log(`  Threshold:       ${threshold} KB`);
  console.log(`  Status:          ${analysis.oversized.length > 0 ? '⚠️  WARNINGS' : '✓ PASS'}\n`);

  // By category
  console.log('Chunks by Category:');
  for (const [category, data] of Object.entries(analysis.byCategory)) {
    if (data.count > 0) {
      console.log(
        `  ${category.padEnd(12)} ${data.count.toString().padStart(3)} chunks  ${formatSize(data.sizeKB).padStart(10)}`
      );
    }
  }
  console.log('');

  // Warnings
  if (analysis.oversized.length > 0) {
    console.log(`⚠️  Found ${analysis.oversized.length} oversized chunk(s):\n`);
    for (const chunk of analysis.oversized) {
      console.log(
        `  ❌ ${chunk.name}\n` +
        `     Type: ${chunk.category}\n` +
        `     Size: ${chunk.sizeKB} KB (exceeds threshold by ${chunk.overBy} KB)\n`
      );
    }
  } else {
    console.log('✓ All chunks are within the size threshold.\n');
  }

  // Detailed breakdown
  if (verbose && analysis.details.length > 0) {
    console.log('Detailed Breakdown:');
    console.log('─'.repeat(72));

    // Sort by size descending
    const sorted = [...analysis.details].sort((a, b) => b.sizeKB - a.sizeKB);

    for (const chunk of sorted) {
      const status = chunk.status === 'oversized' ? '❌' : '✓';
      const size = formatSize(chunk.sizeKB).padStart(10);
      const name = chunk.name.padEnd(45);
      const category = chunk.category.padEnd(12);
      console.log(`  ${status} ${name} ${category} ${size}`);
    }
    console.log('');
  }

  console.log('═'.repeat(64));
}

/**
 * Print analysis results in JSON format
 */
function printJsonResults(analysis) {
  const output = {
    summary: {
      totalChunks: analysis.total,
      totalSizeKB: analysis.totalSizeKB,
      oversizedCount: analysis.oversized.length,
    },
    byCategory: analysis.byCategory,
    oversized: analysis.oversized,
    details: analysis.details,
  };

  console.log(JSON.stringify(output, null, 2));
}

/**
 * Main execution
 */
function main() {
  const options = parseArgs();

  if (options.help) {
    showHelp();
    process.exit(0);
  }

  try {
    // Validate threshold
    if (isNaN(options.threshold) || options.threshold <= 0) {
      console.error('Error: Threshold must be a positive number');
      process.exit(1);
    }

    // Get and analyze chunks
    const chunks = getChunkFiles();

    if (chunks.length === 0) {
      console.error('Error: No JavaScript chunks found in dist/assets');
      console.error('Please build the frontend first: npm run build');
      process.exit(1);
    }

    const analysis = analyzeChunks(chunks, options.threshold);

    // Output results
    if (options.json) {
      printJsonResults(analysis);
    } else {
      printResults(analysis, options.threshold, options.verbose);
    }

    // Exit with error if oversized chunks found and fail-on-warning is set
    if (options.failOnWarning && analysis.oversized.length > 0) {
      process.exit(1);
    }

    process.exit(0);
  } catch (error) {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

// Run if executed directly
const modulePath = fileURLToPath(import.meta.url);
if (process.argv[1] === modulePath) {
  main();
}

export { main, analyzeChunks, getChunkFiles, categorizeChunk };
