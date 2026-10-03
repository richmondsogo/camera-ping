import { test, expect } from "@playwright/test";

test.describe("Camera Management & Dashboard CRUD", () => {
  test("full CRUD flow: add, filter, edit, and delete cameras", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Camera Monitor/);

    // 1. Initial Empty State
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" })
    ).toBeVisible();

    const emptyState = page.getByTestId("empty-cameras-state");
    await expect(emptyState).toBeVisible();
    await expect(emptyState).toHaveText(
      "No cameras yet. Add your first camera to start monitoring."
    );

    // Verify search and filter controls are disabled when camera count is 0
    await expect(page.getByTestId("camera-search-input")).toBeDisabled();
    await expect(page.getByTestId("status-filter-trigger")).toBeDisabled();
    await expect(page.getByTestId("location-filter-trigger")).toBeDisabled();

    // Verify toolbar Add Camera button is enabled
    const addToolbarBtn = page.getByTestId("add-camera-toolbar-button");
    await expect(addToolbarBtn).toBeEnabled();

    // Verify count line for 0 cameras
    await expect(page.getByTestId("camera-count-line")).toHaveText(
      "Showing 0 of 0 cameras"
    );

    // 2. Add First Camera (RFC 5737 documentation block 192.0.2.0/24)
    await addToolbarBtn.click();
    const formDialog = page.getByTestId("camera-form-dialog");
    await expect(formDialog).toBeVisible();
    await expect(page.getByTestId("dialog-title")).toHaveText("Add Camera");

    await page.getByTestId("camera-name-input").fill("Front Gate PTZ");
    await page.getByTestId("camera-ip-input").fill("192.0.2.10");
    await page.getByTestId("camera-location-input").fill("Main Gate");
    await page
      .getByTestId("camera-description-input")
      .fill("Primary entrance monitoring camera");

    await page.getByTestId("submit-camera-form-button").click();
    await expect(formDialog).not.toBeVisible();

    // Verify first camera rendered in table
    await expect(page.getByText("Front Gate PTZ")).toBeVisible();
    await expect(page.getByText("192.0.2.10")).toBeVisible();
    await expect(page.getByText("Main Gate")).toBeVisible();

    // Verify count line uses singular "camera"
    await expect(page.getByTestId("camera-count-line")).toHaveText(
      "Showing 1 of 1 camera"
    );

    // Verify search and filter controls are now enabled
    await expect(page.getByTestId("camera-search-input")).toBeEnabled();
    await expect(page.getByTestId("status-filter-trigger")).toBeEnabled();
    await expect(page.getByTestId("location-filter-trigger")).toBeEnabled();

    // 3. Add Second Camera
    await addToolbarBtn.click();
    await expect(formDialog).toBeVisible();

    await page.getByTestId("camera-name-input").fill("Warehouse East");
    await page.getByTestId("camera-ip-input").fill("192.0.2.20");
    await page.getByTestId("camera-location-input").fill("Warehouse");
    await page
      .getByTestId("camera-description-input")
      .fill("Loading dock overview camera");

    await page.getByTestId("submit-camera-form-button").click();
    await expect(formDialog).not.toBeVisible();

    await expect(page.getByText("Warehouse East")).toBeVisible();
    await expect(page.getByTestId("camera-count-line")).toHaveText(
      "Showing 2 of 2 cameras"
    );

    // 4. Search and Filter
    const searchInput = page.getByTestId("camera-search-input");
    await searchInput.fill("Warehouse");
    await expect(page.getByText("Warehouse East")).toBeVisible();
    await expect(
      page.locator("tbody").getByText("Front Gate PTZ")
    ).not.toBeVisible();
    await expect(page.getByTestId("camera-count-line")).toHaveText(
      "Showing 1 of 2 cameras"
    );

    // Clear search
    await searchInput.fill("");
    await expect(page.getByText("Front Gate PTZ")).toBeVisible();
    await expect(page.getByText("Warehouse East")).toBeVisible();
    await expect(page.getByTestId("camera-count-line")).toHaveText(
      "Showing 2 of 2 cameras"
    );

    // 5. Edit Camera
    const editFirstBtn = page
      .locator("tr", { hasText: "Front Gate PTZ" })
      .getByRole("button", { name: /^Edit/ });
    await editFirstBtn.click();

    await expect(formDialog).toBeVisible();
    await expect(page.getByTestId("dialog-title")).toHaveText("Edit Camera");
    await expect(page.getByTestId("camera-name-input")).toHaveValue(
      "Front Gate PTZ"
    );

    // Update location and description
    await page.getByTestId("camera-location-input").fill("North Entrance");
    await page
      .getByTestId("camera-description-input")
      .fill("Updated perimeter description");

    await page.getByTestId("submit-camera-form-button").click();
    await expect(formDialog).not.toBeVisible();

    await expect(page.getByText("North Entrance")).toBeVisible();
    await expect(page.getByText("Updated perimeter description")).toBeVisible();

    // 6. Delete Cameras
    // Delete Warehouse East
    const deleteWarehouseBtn = page
      .locator("tr", { hasText: "Warehouse East" })
      .getByRole("button", { name: /^Delete/ });
    await deleteWarehouseBtn.click();

    const deleteDialog = page.getByTestId("delete-camera-dialog");
    await expect(deleteDialog).toBeVisible();
    await expect(page.getByTestId("delete-dialog-title")).toHaveText(
      "Delete Camera"
    );

    await page.getByTestId("confirm-delete-camera-button").click();
    await expect(deleteDialog).not.toBeVisible();
    await expect(
      page.locator("tbody").getByText("Warehouse East")
    ).not.toBeVisible();
    await expect(page.getByTestId("camera-count-line")).toHaveText(
      "Showing 1 of 1 camera"
    );

    // Delete Front Gate PTZ
    const deleteFrontBtn = page
      .locator("tr", { hasText: "Front Gate PTZ" })
      .getByRole("button", { name: /^Delete/ });
    await deleteFrontBtn.click();
    await expect(deleteDialog).toBeVisible();

    await page.getByTestId("confirm-delete-camera-button").click();
    await expect(deleteDialog).not.toBeVisible();
    await expect(
      page.locator("tbody").getByText("Front Gate PTZ")
    ).not.toBeVisible();

    // Verify back to empty state
    await expect(emptyState).toBeVisible();
    await expect(page.getByTestId("camera-count-line")).toHaveText(
      "Showing 0 of 0 cameras"
    );
  });

  test("column fit at 1280px viewport and table scroll container at 1024px viewport", async ({
    page,
  }) => {
    // Read-only mock via page.route as specified in amendment 16
    await page.route("**/api/cameras", async (route) => {
      const craftedCameras = [
        {
          id: 99,
          camera_name: "North Perimeter High Res",
          ip_address: "255.255.255.254",
          location: "Perimeter Sector 7",
          description:
            "Continuous 24/7 high definition monitoring coverage for outer perimeter fence line.",
          status: "offline",
          last_checked: "2026-12-31T23:59:59Z",
          last_online: "2026-12-30T10:00:00Z",
          created_at: "2026-10-01T08:00:00Z",
          updated_at: "2026-10-01T08:00:00Z",
        },
      ];
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(craftedCameras),
      });
    });

    // 1. Assert at 1280px viewport that fixed columns are NOT truncated
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");

    const row = page.getByTestId("camera-row-99");
    await expect(row).toBeVisible();

    // Status column: dot + "Offline" text
    const statusCell = row.locator("td.w-col-status");
    await expect(statusCell).toBeVisible();
    const statusFits = await statusCell.evaluate(
      (el) => el.scrollWidth <= el.clientWidth
    );
    expect(statusFits).toBe(true);

    // IP Address column: longest valid IP 255.255.255.254
    const ipCell = row.locator("td.w-col-ip");
    await expect(ipCell).toBeVisible();
    const ipFits = await ipCell.evaluate(
      (el) => el.scrollWidth <= el.clientWidth
    );
    expect(ipFits).toBe(true);

    // Last Checked column: full timestamp 2026-12-31 23:59:59
    const checkedCell = row.locator("td.w-col-checked");
    await expect(checkedCell).toBeVisible();
    const checkedFits = await checkedCell.evaluate(
      (el) => el.scrollWidth <= el.clientWidth
    );
    expect(checkedFits).toBe(true);

    // Actions column: Edit and Delete buttons
    const actionsCell = row.locator("td.w-col-actions");
    await expect(actionsCell).toBeVisible();
    const actionsFit = await actionsCell.evaluate(
      (el) => el.scrollWidth <= el.clientWidth
    );
    expect(actionsFit).toBe(true);

    // 2. Assert at 1024px viewport that the table scrolls inside its wrapper while body has no horizontal overflow
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.waitForTimeout(200);

    const tableContainer = page.getByTestId("camera-table-container");
    const containerScrolls = await tableContainer.evaluate(
      (el) => el.scrollWidth > el.clientWidth
    );
    expect(containerScrolls).toBe(true);

    // document.body has NO horizontal overflow
    const bodyHasNoOverflow = await page.evaluate(() => {
      return (
        document.body.scrollWidth <=
        Math.max(document.documentElement.clientWidth, window.innerWidth)
      );
    });
    expect(bodyHasNoOverflow).toBe(true);
  });
});
