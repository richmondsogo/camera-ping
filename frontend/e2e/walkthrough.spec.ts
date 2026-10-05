import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test, expect } from "@playwright/test";
import { resetCameras, resetSettings, seedCameras, stopMonitoring } from "./helpers";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const screenshotsDir = path.resolve(__dirname, "../screenshots/step09");

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

test.describe("Step 09: Browser & Accessibility Verification Walkthrough", () => {
  test.beforeEach(async () => {
    await resetCameras();
    await resetSettings(60); // Default 60s
  });

  test.afterEach(async () => {
    await stopMonitoring();
    await resetSettings(10); // Restore 10s for other e2e tests
  });

  test("execute 6-point screenshot walkthrough and responsive inspection", async ({
    page,
  }) => {
    // 1. Seed cameras to have rich dashboard data
    await seedCameras(30);

    // Set standard viewport
    await page.setViewportSize({ width: 1280, height: 900 });

    // Step 1: Default Settings Page (Light Mode)
    await page.goto("/settings");
    await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
    await expect(page.getByTestId("interval-preset-select")).toHaveText(/1 minute/);
    await expect(page.getByTestId("theme-select")).toHaveText(/Light/);

    await page.screenshot({
      path: path.join(screenshotsDir, "01-settings-default-light.png"),
      fullPage: true,
    });

    // Step 2: Custom Interval "2 hours", Long Interval Warning, Dirty state
    await page.getByTestId("interval-preset-select").click();
    await page.getByRole("option", { name: "Custom…" }).click();

    const amountInput = page.getByTestId("custom-interval-amount");
    const unitSelect = page.getByTestId("custom-interval-unit");
    await amountInput.fill("2");
    await unitSelect.click();
    await page.getByRole("option", { name: "hours" }).click();

    const saveButton = page.getByTestId("save-settings-button");
    await expect(saveButton).toBeEnabled();
    const warning = page.getByTestId("long-interval-warning");
    await expect(warning).toHaveText("Outages may take up to 2 hours to detect.");

    await page.screenshot({
      path: path.join(screenshotsDir, "02-settings-custom-dirty.png"),
      fullPage: true,
    });

    // Step 3: Save and verify "Saved." notice
    await saveButton.click();
    const savedNotice = page.getByTestId("saved-notice");
    await expect(savedNotice).toHaveText("Saved.");
    await expect(page.getByTestId("settings-live-region")).toHaveText("Settings saved.");

    await page.screenshot({
      path: path.join(screenshotsDir, "03-settings-saved-notice.png"),
      fullPage: true,
    });

    // Step 4: Appearance -> Switch to Dark Mode on Settings Page
    const themeSelect = page.getByTestId("theme-select");
    await themeSelect.click();
    await page.getByRole("option", { name: "Dark" }).click();
    await expect(page.locator("html")).toHaveClass(/dark/);

    await page.screenshot({
      path: path.join(screenshotsDir, "04-settings-dark-mode.png"),
      fullPage: true,
    });

    // Step 5: Dashboard in Dark Mode reflecting 2 hours check interval
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1, name: "Dashboard" })).toBeVisible();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await expect(page.getByTestId("check-interval")).toHaveText(/Checks every 2 hours/);

    await page.screenshot({
      path: path.join(screenshotsDir, "05-dashboard-dark-mode.png"),
      fullPage: true,
    });

    // Step 6: Settings Page Custom Interval Error State
    await page.goto("/settings");
    await page.getByTestId("custom-interval-amount").fill("5");
    await page.getByTestId("custom-interval-unit").click();
    await page.getByRole("option", { name: "seconds" }).click();

    const errorMsg = page.getByTestId("custom-interval-error");
    await expect(errorMsg).toHaveText("Choose an interval between 10 seconds and 365 days.");
    await expect(page.getByTestId("save-settings-button")).toBeDisabled();

    await page.screenshot({
      path: path.join(screenshotsDir, "06-settings-custom-error.png"),
      fullPage: true,
    });

    // Restore light theme for clean environment
    await page.getByTestId("theme-select").click();
    await page.getByRole("option", { name: "Light" }).click();
    await expect(page.locator("html")).not.toHaveClass(/dark/);
  });

  test("responsive viewport verification (1000px, 1280px, 1920px)", async ({
    page,
  }) => {
    for (const width of [1000, 1280, 1920]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/settings");
      await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();

      // Check no horizontal scrollbar on body
      const scrollWidth = await page.evaluate(
        () => document.documentElement.scrollWidth
      );
      const clientWidth = await page.evaluate(
        () => document.documentElement.clientWidth
      );
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1);

      // Verify max width constraint on main container
      const containerBox = await page.getByTestId("settings-page").boundingBox();
      expect(containerBox).not.toBeNull();
      if (width > 1200) {
        expect(containerBox!.width).toBeLessThanOrEqual(1200 + 48); // max-w-page (1200px + padding)
      }
    }
  });

  test("accessibility audit: headings, form labels, aria-invalid, and focus visible", async ({
    page,
  }) => {
    await page.goto("/settings");

    // 1. Heading hierarchy
    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toHaveText("Settings");

    const h2s = page.getByRole("heading", { level: 2 });
    await expect(h2s.nth(0)).toHaveText("Monitoring");
    await expect(h2s.nth(1)).toHaveText("Appearance");

    // 2. Form controls have accessible names
    await expect(page.getByLabel("Check Interval")).toBeVisible();
    await expect(page.getByLabel("Theme")).toBeVisible();

    // 3. Focus visible ring on Tab navigation
    await page.keyboard.press("Tab"); // Skip or nav
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab"); // Into settings content

    const focusedElement = page.locator(":focus");
    await expect(focusedElement).toBeVisible();

    // 4. Custom row aria-invalid and aria-describedby linkage
    await page.getByTestId("interval-preset-select").click();
    await page.getByRole("option", { name: "Custom…" }).click();

    const amountInput = page.getByTestId("custom-interval-amount");
    await amountInput.fill("");
    await expect(amountInput).toHaveAttribute("aria-invalid", "true");
    await expect(amountInput).toHaveAttribute("aria-describedby", "custom-interval-error");
  });
});
