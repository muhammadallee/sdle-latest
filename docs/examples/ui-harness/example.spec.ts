// A sample check. Names cite the screen id (UI-HOME-1) and the state, so a report case can be traced back
// to the plan's User Interface section. Use synthetic data and test-only accounts.
import { test, expect } from '@playwright/test';

const baseURL = process.env.BASE_URL ?? 'http://localhost:4200';

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 820, height: 1180 },
]) {
  test(`UI-HOME-1 ${viewport.name} loaded: the page renders without horizontal overflow`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto(baseURL, { waitUntil: 'networkidle' });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    // testInfo.outputPath() lives under the harness's configured output directory, which is ignored by git.
    await page.screenshot({ path: testInfo.outputPath(`UI-HOME-1-${viewport.name}-loaded.png`) });
  });
}
