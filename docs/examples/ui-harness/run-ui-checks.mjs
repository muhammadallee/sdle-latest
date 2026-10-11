// Example browser-check harness for an SDLE implementation manifest. Not exercised by SDLE's CI.
//
//   node run-ui-checks.mjs [config.json]
//
// Pass it to the manifest build as ONE command, and its report with --junit:
//   manifest build --test-command "node run-ui-checks.mjs ui-harness.config.json" --junit <junitPath>
//
// Exit codes: 0 all checks passed · 1 a check failed · 78 the environment is not ready (nothing ran).
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { createRequire } from 'node:module';

const EX_CONFIG = 78;
const configPath = process.argv[2] ?? 'ui-harness.config.json';
const config = JSON.parse(readFileSync(configPath, 'utf8'));
const { baseUrl, specDir, junitPath, outputDir, browser = 'chromium', timeoutMs = 120000 } = config;

function notReady(reason) {
  console.error(`ui-harness: environment not ready: ${reason}`);
  process.exit(EX_CONFIG);
}

// 1. preflight: the runner, the browser and the app must be there before any check runs.
const require = createRequire(resolve('package.json'));
let playwright;
try {
  playwright = require('@playwright/test');
} catch {
  notReady('@playwright/test is not installed');
}
const executable = playwright[browser]?.executablePath?.();
if (!executable || !existsSync(executable)) notReady(`browser "${browser}" is not installed`);
try {
  const response = await fetch(baseUrl, { signal: AbortSignal.timeout(5000) });
  if (!response.ok) notReady(`${baseUrl} answered ${response.status}`);
} catch {
  notReady(`${baseUrl} is not reachable`);
}

// 2. one merged JUnit report, in an ignored path; screenshots and traces beside it.
mkdirSync(dirname(resolve(junitPath)), { recursive: true });
mkdirSync(resolve(outputDir), { recursive: true });
const cli = require.resolve('@playwright/test/cli');
const args = [cli, 'test', specDir, '--reporter=junit', `--output=${outputDir}`, `--browser=${browser}`];
const run = spawnSync(process.execPath, args, {
  stdio: 'inherit',
  timeout: timeoutMs,
  env: { ...process.env, PLAYWRIGHT_JUNIT_OUTPUT_FILE: resolve(junitPath), BASE_URL: baseUrl },
});
process.exit(run.status ?? 1);
