import { test, expect } from "@playwright/test";

test("smoke test: loads page and verifies health check", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Camera Monitor/);
  await expect(
    page.getByRole("heading", { name: "Camera Monitor" })
  ).toBeVisible();
  await expect(page.getByText("Backend Health:")).toBeVisible();
  await expect(page.getByText("ok")).toBeVisible();
});
