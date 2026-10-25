// A sample automated accessibility scan, one per screen and state the plan lists. It catches what a functional
// check and a screenshot miss (text contrast, missing labels and names, broken landmarks); it does not establish
// keyboard or screen-reader behaviour, which needs its own checks. Scoped to the screen's own element, so problems
// elsewhere in the application shell are reported by the checks for those screens, not this one.
//
// Needs @axe-core/playwright beside @playwright/test.
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const baseURL = process.env.BASE_URL ?? 'http://localhost:4200';
const SCREEN = { id: 'UI-HOME-1', path: '/', element: 'main' };   // replace with the plan's screen id, route and root element

for (const viewport of [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 820, height: 1180 },
]) {
  test(`${SCREEN.id} ${viewport.name} loaded: no automated accessibility violations`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto(new URL(SCREEN.path, baseURL).toString(), { waitUntil: 'networkidle' });
    const results = await new AxeBuilder({ page })
      .include(SCREEN.element)
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const summary = results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(', ');
    expect(results.violations, summary).toEqual([]);
  });
}
