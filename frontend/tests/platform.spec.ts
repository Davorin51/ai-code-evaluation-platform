import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdirSync } from "node:fs";
const shots = "../docs/screenshots";
test("real backend workflow, reports, comparison, responsive layouts and accessibility", async ({
  page,
  request,
}) => {
  mkdirSync(shots, { recursive: true });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Evaluation overview", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Trusted-example evaluation mode", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open workspace" }).click();
  await expect(
    page.getByRole("textbox", { name: "Python candidate solution editor" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run Evaluation" }).click();
  const report = page.getByRole("region", { name: "Evaluation report" });
  await expect(report.getByText("3/5 passed", { exact: true })).toBeVisible();
  await report.getByText("no-reuse", { exact: true }).click();
  await expect(
    report
      .locator("details.test-case")
      .filter({ hasText: "no-reuse" })
      .getByText("Returned value differs from the challenge contract", {
        exact: true,
      }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: shots + "/workspace.png", fullPage: true });
  const downloadPromise = page.waitForEvent("download");
  await report.getByRole("link", { name: "PDF", exact: false }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);
  await page
    .getByLabel("Example solution", { exact: true })
    .selectOption("reference");
  await page.getByRole("button", { name: "Run Evaluation" }).click();
  await expect(report.getByText("5/5 passed", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Overview", exact: false })
    .first()
    .click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.setViewportSize({ width: 1440, height: 1350 });
  await page.screenshot({ path: shots + "/overview.png", fullPage: true });
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(axe.violations).toEqual([]);
  await page
    .getByRole("button", { name: "Compare", exact: false })
    .first()
    .click();
  const submissions = await (
    await request.get("http://127.0.0.1:8000/api/submissions")
  ).json();
  await page
    .getByLabel("Baseline submission", { exact: true })
    .selectOption(submissions[1].id);
  await page
    .getByLabel("Candidate submission", { exact: true })
    .selectOption(submissions[0].id);
  await page
    .getByRole("main")
    .getByRole("button", { name: "Compare", exact: true })
    .click();
  await expect(
    page.getByText("40 percentage points", { exact: true }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: shots + "/comparison.png", fullPage: true });
  await page.getByRole("button", { name: "History", exact: false }).click();
  await page.getByRole("button", { name: "View Buggy example" }).click();
  await expect(report.getByText("3/5 passed", { exact: true })).toBeVisible();
  const malformed = await request.post(
    "http://127.0.0.1:8000/api/submissions",
    {
      data: {
        challenge_id: "two-sum",
        variant: "reference",
        code: "print(123)",
      },
    },
  );
  expect(malformed.status()).toBe(422);
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 1050 });
    for (const tab of ["Overview", "Challenges", "History", "Compare"]) {
      await page
        .getByRole("button", { name: tab, exact: false })
        .first()
        .click();
      const geometry = await page.evaluate(() => ({
        viewport: innerWidth,
        width: document.documentElement.scrollWidth,
        overflow: [...document.querySelectorAll("*")]
          .map((el) => ({
            tag: el.tagName,
            cls: el.className.toString().slice(0, 100),
            left: el.getBoundingClientRect().left,
            right: el.getBoundingClientRect().right,
          }))
          .filter((el) => el.right > innerWidth + 1 || el.left < -1)
          .slice(0, 25),
      }));
      if (geometry.width > geometry.viewport)
        await page.screenshot({
          path: shots + `/overflow-${width}-${tab}.png`,
          fullPage: true,
        });
      expect(
        geometry.width,
        JSON.stringify({ tab, ...geometry }),
      ).toBeLessThanOrEqual(geometry.viewport);
    }
    await page
      .getByRole("button", { name: "Overview", exact: false })
      .first()
      .click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: shots + `/overview-${width}.png`,
      fullPage: true,
    });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.keyboard.press("Tab");
  expect(errors).toEqual([]);
});
