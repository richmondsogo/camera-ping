import { test, expect } from "@playwright/test";

test("smoke test: renders app shell and navigates between routes", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/Camera Monitor/);

  // App shell header
  await expect(page.getByText("Camera Monitor")).toBeVisible();
  const mainNav = page.getByRole("navigation", { name: "Main" });
  await expect(mainNav).toBeVisible();

  // Dashboard initial route
  const dashboardLink = mainNav.getByRole("link", { name: "Dashboard" });
  const settingsLink = mainNav.getByRole("link", { name: "Settings" });
  await expect(dashboardLink).toHaveAttribute("aria-current", "page");
  await expect(settingsLink).not.toHaveAttribute("aria-current");
  await expect(
    page.getByRole("heading", { level: 1, name: "Dashboard" })
  ).toBeVisible();

  // Navigate to Settings
  await settingsLink.click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Settings" })
  ).toBeVisible();
  await expect(settingsLink).toHaveAttribute("aria-current", "page");
  await expect(dashboardLink).not.toHaveAttribute("aria-current");

  // Navigate back to Dashboard
  await dashboardLink.click();
  await expect(page).toHaveURL(/\/#?$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Dashboard" })
  ).toBeVisible();
  await expect(dashboardLink).toHaveAttribute("aria-current", "page");
});
