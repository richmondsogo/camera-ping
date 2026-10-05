import { test, expect } from "@playwright/test";
import { resetSettings, stopMonitoring } from "./helpers";

test.describe("Settings Page & Configuration", () => {
  test.beforeEach(async () => {
    // Reset interval to default 10s for e2e environment
    await resetSettings(10);
  });

  test.afterEach(async () => {
    await stopMonitoring();
    await resetSettings(10);
  });

  test("offline save error and recovery (Amendment 4)", async ({
    page,
    context,
  }) => {
    await page.goto("/settings");
    await expect(
      page.getByRole("heading", { level: 1, name: "Settings" })
    ).toBeVisible();

    const presetSelect = page.getByTestId("interval-preset-select");
    await expect(presetSelect).toBeVisible();

    // 1. Emulate offline
    await context.setOffline(true);

    // 2. Change the interval to a different preset (30 seconds)
    await presetSelect.click();
    await page.getByRole("option", { name: "30 seconds" }).click();

    // 3. Click Save button
    const saveButton = page.getByTestId("save-settings-button");
    await expect(saveButton).toBeEnabled();
    await saveButton.click();

    // 4. Expect role="alert" message "Couldn't save settings. Try again."
    const alertMessage = page.getByTestId("save-error-message");
    await expect(alertMessage).toBeVisible();
    await expect(alertMessage).toHaveText("Couldn't save settings. Try again.");

    // 5. Expect Save button re-enabled and control still showing the unsaved value
    await expect(saveButton).toBeEnabled();
    await expect(presetSelect).toHaveText(/30 seconds/);

    // 6. Go back online
    await context.setOffline(false);

    // 7. Click Save again -> succeeds
    await saveButton.click();
    await expect(page.getByTestId("saved-notice")).toHaveText("Saved.");
    await expect(page.getByTestId("settings-live-region")).toHaveText(
      "Settings saved."
    );
  });

  test("preset interval save and reload persistence", async ({ page }) => {
    await page.goto("/settings");
    const presetSelect = page.getByTestId("interval-preset-select");
    await expect(presetSelect).toBeVisible();

    // Change to 1 minute
    await presetSelect.click();
    await page.getByRole("option", { name: "1 minute" }).click();

    const saveButton = page.getByTestId("save-settings-button");
    await expect(saveButton).toBeEnabled();
    await saveButton.click();

    await expect(page.getByTestId("saved-notice")).toHaveText("Saved.");

    // Reload page and verify persisted
    await page.reload();
    await expect(page.getByTestId("interval-preset-select")).toHaveText(
      /1 minute/
    );
  });

  test("custom interval 2 hours save, warning, and reload persistence", async ({
    page,
  }) => {
    await page.goto("/settings");
    const presetSelect = page.getByTestId("interval-preset-select");
    await expect(presetSelect).toBeVisible();

    // Switch to Custom…
    await presetSelect.click();
    await page.getByRole("option", { name: "Custom…" }).click();

    const amountInput = page.getByTestId("custom-interval-amount");
    const unitSelect = page.getByTestId("custom-interval-unit");

    await expect(amountInput).toBeVisible();
    await expect(unitSelect).toBeVisible();

    // Enter 2 hours
    await amountInput.fill("2");
    await unitSelect.click();
    await page.getByRole("option", { name: "hours" }).click();

    // Long interval warning should be visible
    await expect(page.getByTestId("long-interval-warning")).toHaveText(
      "Outages may take up to 2 hours to detect."
    );

    // Click Save
    const saveButton = page.getByTestId("save-settings-button");
    await expect(saveButton).toBeEnabled();
    await saveButton.click();

    await expect(page.getByTestId("saved-notice")).toHaveText("Saved.");

    // Reload and verify
    await page.reload();
    await expect(page.getByTestId("interval-preset-select")).toHaveText(
      /Custom…/
    );
    await expect(page.getByTestId("custom-interval-amount")).toHaveValue("2");
    await expect(page.getByTestId("custom-interval-unit")).toHaveText(/hours/);
    await expect(page.getByTestId("long-interval-warning")).toHaveText(
      "Outages may take up to 2 hours to detect."
    );
  });

  test("custom 1 day interval displays calendar date in dashboard next check", async ({
    page,
  }) => {
    // 1. Configure 1 day on Settings page
    await page.goto("/settings");
    await page.getByTestId("interval-preset-select").click();
    await page.getByRole("option", { name: "Custom…" }).click();

    await page.getByTestId("custom-interval-amount").fill("1");
    await page.getByTestId("custom-interval-unit").click();
    await page.getByRole("option", { name: "days", exact: true }).click();

    await page.getByTestId("save-settings-button").click();
    await expect(page.getByTestId("saved-notice")).toHaveText("Saved.");

    // 2. Start monitoring on Dashboard
    await page.goto("/");
    const startButton = page.getByTestId("start-monitoring-button");
    await startButton.click();

    // Wait until running and next check shows calendar date format (not just HH:mm:ss)
    const nextCheck = page.getByTestId("next-check");
    await expect(nextCheck).toBeVisible();
    // 1 day in future will cross to tomorrow, showing Month Day, HH:mm:ss
    await expect(nextCheck).toHaveText(
      /Next check [A-Z][a-z]{2}\s+\d+,\s+\d{2}:\d{2}:\d{2}/,
      {
        timeout: 15_000,
      }
    );

    // Stop monitoring
    await page.getByTestId("stop-monitoring-button").click();
  });

  test("invalid custom inputs disable Save button and show error messages", async ({
    page,
  }) => {
    await page.goto("/settings");
    await page.getByTestId("interval-preset-select").click();
    await page.getByRole("option", { name: "Custom…" }).click();

    const amountInput = page.getByTestId("custom-interval-amount");
    const saveButton = page.getByTestId("save-settings-button");

    // Empty input
    await amountInput.fill("");
    await expect(page.getByTestId("custom-interval-error")).toHaveText(
      "Enter an interval amount."
    );
    await expect(saveButton).toBeDisabled();

    // Less than 10 seconds
    await page.getByTestId("custom-interval-unit").click();
    await page.getByRole("option", { name: "seconds" }).click();
    await amountInput.fill("5");
    await expect(page.getByTestId("custom-interval-error")).toHaveText(
      "Choose an interval between 10 seconds and 365 days."
    );
    await expect(saveButton).toBeDisabled();

    // Non-digits
    await amountInput.fill("abc");
    await expect(page.getByTestId("custom-interval-error")).toHaveText(
      "Enter a whole number of seconds."
    );
    await expect(saveButton).toBeDisabled();
  });

  test("theme toggle immediately switches theme and persists across reloads", async ({
    page,
  }) => {
    await page.goto("/settings");
    const themeSelect = page.getByTestId("theme-select");
    await expect(themeSelect).toBeVisible();

    // Initially light mode
    await expect(page.locator("html")).not.toHaveClass(/dark/);

    // Switch to Dark
    await themeSelect.click();
    await page.getByRole("option", { name: "Dark" }).click();

    await expect(page.locator("html")).toHaveClass(/dark/);
    await expect(themeSelect).toHaveText(/Dark/);

    // Reload page -> dark remains
    await page.reload();
    await expect(page.locator("html")).toHaveClass(/dark/);
    await expect(page.getByTestId("theme-select")).toHaveText(/Dark/);

    // Switch back to Light
    await page.getByTestId("theme-select").click();
    await page.getByRole("option", { name: "Light" }).click();

    await expect(page.locator("html")).not.toHaveClass(/dark/);

    // Reload page -> light remains
    await page.reload();
    await expect(page.locator("html")).not.toHaveClass(/dark/);
  });

  test("no-theme-flash proof: dark class is applied before main.tsx executes", async ({
    page,
  }) => {
    // 1. Seed dark theme in localStorage before navigation
    await page.addInitScript(() => {
      localStorage.setItem("camera-monitor-theme", "dark");
    });

    // 2. Abort main.tsx so React never mounts or executes
    await page.route("**/src/main.tsx", (route) => route.abort());

    // 3. Navigate to page
    await page.goto("/settings", { waitUntil: "domcontentloaded" });

    // 4. Verify that html element already has class 'dark' applied by inline script
    const hasDarkClass = await page.evaluate(() =>
      document.documentElement.classList.contains("dark")
    );
    expect(hasDarkClass).toBe(true);
  });
});
