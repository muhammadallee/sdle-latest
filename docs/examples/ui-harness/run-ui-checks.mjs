// Example browser-check harness for an SDLE implementation manifest. Not exercised by SDLE's CI.
//
//   node run-ui-checks.mjs [config.json]
//
// Pass it to the manifest build as ONE command, and its report with --junit:
//   manifest build --test-command "node run-ui-checks.mjs ui-harness.config.json" --junit <junitPath>
//
// It runs the project's unit command (optional) and the browser checks, and writes ONE merged JUnit report.
// Exit codes: 0 everything passed · 1 a check or the unit command failed · 78 the environment is not ready.
//
// A preflight failure still writes a report, holding one errored case, so the manifest build can record the
// exit code and the gate can refuse it. A report from an earlier run is removed first, so it can never stand in
// for this one.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { createRequire } from 'node:module';

const EX_NOT_READY = 78;
const configPath = process.argv[2] ?? 'ui-harness.config.json';
const config = JSON.parse(readFileSync(configPath, 'utf8'));
const {
  baseUrl, specDir, junitPath, outputDir, browser = 'chromium', timeoutMs = 120000,
  unitCommand = null, unitJunitPath = null,
} = config;

const escapeXml = (text) => String(text).replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' })[c]);
const report = resolve(junitPath);
mkdirSync(dirname(report), { recursive: true });
mkdirSync(resolve(outputDir), { recursive: true });
rmSync(report, { force: true });
if (unitJunitPath) rmSync(resolve(unitJunitPath), { force: true });

function notReady(reason) {
  console.error(`ui-harness: environment not ready: ${reason}`);
  writeFileSync(report,
    '<?xml version="1.0" encoding="UTF-8"?>\n<testsuites tests="1" errors="1">\n' +
    '<testsuite name="ui-harness preflight" tests="1" errors="1">\n' +
    '<testcase name="environment preflight" classname="ui-harness">' +
    `<error message="${escapeXml(reason)}"/></testcase>\n</testsuite>\n</testsuites>\n`);
  process.exit(EX_NOT_READY);
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

// 2. the project's unit command, if any, then the browser checks. Both always run, so one report shows both.
let failed = false;
if (unitCommand) {
  const [program, ...args] = unitCommand;
  const unit = spawnSync(program, args, { stdio: 'inherit', timeout: timeoutMs });
  if (unit.status !== 0) failed = true;
}
const browserReport = resolve(outputDir, 'browser-junit.xml');
const cli = require.resolve('@playwright/test/cli');
const run = spawnSync(process.execPath,
  [cli, 'test', specDir, '--reporter=junit', `--output=${resolve(outputDir, 'artifacts')}`, `--browser=${browser}`], {
    stdio: 'inherit',
    timeout: timeoutMs,
    env: { ...process.env, PLAYWRIGHT_JUNIT_OUTPUT_FILE: browserReport, BASE_URL: baseUrl,
           UI_ARTIFACT_DIR: resolve(outputDir, 'artifacts') },
  });
if (run.status !== 0) failed = true;

// 3. one merged report: every <testsuite> from each source, kept as it was written.
const suites = [];
for (const source of [unitJunitPath && resolve(unitJunitPath), browserReport]) {
  if (source && existsSync(source)) {
    suites.push(...(readFileSync(source, 'utf8').match(/<testsuite[\s>][\s\S]*?<\/testsuite>/g) ?? []));
  }
}
if (suites.length === 0) failed = true;
writeFileSync(report,
  `<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n${suites.join('\n')}\n</testsuites>\n`);
process.exit(failed ? 1 : 0);
