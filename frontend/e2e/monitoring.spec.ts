import { test, expect } from "@playwright/test";
import { resetCameras, stopMonitoring } from "./helpers";

test.describe("Monitoring Engine & Dashboard Controls", () => {
  test.beforeEach(async () => {
    await resetCameras();
  });

  test.afterEach(async () => {
    await stopMonitoring();
  });

  test("live monitoring cycle: loopback camera goes online, doc IP goes offline with increasing check count, and stopping persists stopped notice", async ({
    page,
    request,
  }) => {
    // 1. Seed two cameras: one loopback (online) and one RFC 5737 doc IP (offline)
    const seedRes1 = await request.post("http://127.0.0.1:18000/api/cameras", {
      data: {
        camera_name: "Loopback Cam",
        location: "Server Room",
        description: "Local loopback interface",
        ip_address: "127.0.0.1",
      },
    });
    expect(seedRes1.ok()).toBeTruthy();

    const seedRes2 = await request.post("http://127.0.0.1:18000/api/cameras", {
      data: {
        camera_name: "Doc IP Cam",
        location: "Warehouse",
        description: "Non-routable doc IP",
        ip_address: "192.0.2.1",
      },
    });
    expect(seedRes2.ok()).toBeTruthy();

    await page.goto("/");
    await expect(page).toHaveTitle(/Camera Monitor/);

    // Initial state: Stopped, Start enabled, Stop disabled
    const startButton = page.getByTestId("start-monitoring-button");
    const stopButton = page.getByTestId("stop-monitoring-button");
    await expect(page.getByText("Monitoring stopped")).toBeVisible();
    await expect(startButton).toBeEnabled();
    await expect(stopButton).toBeDisabled();
    await expect(page.getByTestId("stopped-notice")).toBeVisible();

    // 2. Click Start monitoring
    await startButton.click();

    // Monitoring state flips to running; Start disabled, Stop enabled
    await expect(page.getByText("Monitoring running")).toBeVisible();
    await expect(startButton).toBeDisabled();
    await expect(stopButton).toBeEnabled();
    await expect(page.getByTestId("stopped-notice")).not.toBeVisible();

    // 3. Find table rows
    const loopbackRow = page.locator("tbody tr", { hasText: "Loopback Cam" });
    const offlineRow = page.locator("tbody tr", { hasText: "Doc IP Cam" });

    // Wait until Loopback Cam is Online
    await expect(loopbackRow.locator('[data-slot="badge"]')).toHaveText("Online", {
      timeout: 20_000,
    });

    // Wait until Doc IP Cam is Offline and shows a check count
    const checkCountLocator = offlineRow.locator("text=/\\d+\\s+checks?/");
    await expect(checkCountLocator).toBeVisible({ timeout: 20_000 });

    const initialText = await checkCountLocator.innerText();
    const match = initialText.match(/(\d+)/);
    expect(match).not.toBeNull();
    const initialCount = Number.parseInt(match![1], 10);
    const expectedNextText = new RegExp(`^${initialCount + 1}\\s+checks?$`);

    // 4. Wait for the next 10s cycle to complete and check count to increase by 1
    await expect(offlineRow.locator("text=/\\d+\\s+checks?/")).toHaveText(
      expectedNextText,
      { timeout: 25_000 }
    );

    // Verify Loopback Cam stayed Online throughout
    await expect(loopbackRow.locator('[data-slot="badge"]')).toHaveText("Online");

    // Verify Tab Title includes (1 offline)
    await expect(page).toHaveTitle(/\(1 offline\) Camera Monitor/);

    // 5. Click Stop button
    await stopButton.click();

    // Monitoring state returns to stopped; Start enabled, Stop disabled, notice visible
    await expect(page.getByText("Monitoring stopped")).toBeVisible();
    await expect(startButton).toBeEnabled();
    await expect(stopButton).toBeDisabled();
    await expect(page.getByTestId("stopped-notice")).toBeVisible();
  });

  test("resumes running state after page reload", async ({
    page,
    request,
  }) => {
    // Start monitoring via API
    const startRes = await request.post(
      "http://127.0.0.1:18000/api/monitoring/start"
    );
    expect(startRes.ok()).toBeTruthy();

    await page.goto("/");

    // Verify page loads with monitoring running
    await expect(page.getByText("Monitoring running")).toBeVisible();
    await expect(page.getByTestId("start-monitoring-button")).toBeDisabled();
    await expect(page.getByTestId("stop-monitoring-button")).toBeEnabled();

    // Reload page
    await page.reload();

    // Still running after reload
    await expect(page.getByText("Monitoring running")).toBeVisible();
    await expect(page.getByTestId("start-monitoring-button")).toBeDisabled();
    await expect(page.getByTestId("stop-monitoring-button")).toBeEnabled();

    // Stop monitoring via UI
    await page.getByTestId("stop-monitoring-button").click();
    await expect(page.getByText("Monitoring stopped")).toBeVisible();
  });
});
