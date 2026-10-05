import { test, expect } from "@playwright/test";
import { resetCameras } from "./helpers";

test.describe("Production Runtime & Single-Process Serving", () => {
  const prodPort = Number(process.env.E2E_PROD_PORT || "18080");
  const prodBaseUrl = `http://127.0.0.1:${prodPort}`;

  test.beforeEach(async () => {
    await resetCameras(prodBaseUrl);
  });

  test("direct navigation and reload on /settings with clean console and no 404s", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    const notFoundUrls: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    page.on("response", (res) => {
      if (res.status() === 404) {
        notFoundUrls.push(res.url());
      }
    });

    // 1. Direct navigation to client-side route /settings
    await page.goto("/settings");
    await expect(page).toHaveTitle(/Camera Monitor/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Settings" })
    ).toBeVisible();

    // 2. Page reload on /settings
    await page.reload();
    await expect(
      page.getByRole("heading", { level: 1, name: "Settings" })
    ).toBeVisible();

    // 3. Verify clean console and no 404 responses (e.g. no missing favicon or assets)
    expect(consoleErrors).toEqual([]);
    expect(notFoundUrls).toEqual([]);
  });

  test("all outgoing requests are strictly same-origin (excluding data: and blob:)", async ({
    page,
  }) => {
    const requestedUrls: string[] = [];

    page.on("request", (req) => {
      const url = req.url();
      if (!url.startsWith("data:") && !url.startsWith("blob:")) {
        requestedUrls.push(url);
      }
    });

    await page.goto("/");
    await expect(page).toHaveTitle(/Camera Monitor/);
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" })
    ).toBeVisible();

    // Navigate to settings and back
    await page.getByRole("link", { name: "Settings" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Settings" })
    ).toBeVisible();
    await page.getByRole("link", { name: "Dashboard" }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Dashboard" })
    ).toBeVisible();

    expect(requestedUrls.length).toBeGreaterThan(0);
    for (const url of requestedUrls) {
      expect(url.startsWith(prodBaseUrl)).toBe(true);
    }
  });

  test("security headers are present on HTML document and static assets", async ({
    page,
    request,
  }) => {
    // 1. Check document response headers
    const docRes = await request.get("/");
    expect(docRes.status()).toBe(200);
    const docHeaders = docRes.headers();
    expect(docHeaders["x-content-type-options"]).toBe("nosniff");
    expect(docHeaders["x-frame-options"]).toBe("DENY");
    expect(docHeaders["referrer-policy"]).toBe("no-referrer");

    // 2. Load page and find static asset script/link
    await page.goto("/");
    const scriptSrc = await page
      .locator("script[src^='/assets/']")
      .first()
      .getAttribute("src");
    expect(scriptSrc).toBeTruthy();

    if (scriptSrc) {
      const assetRes = await request.get(scriptSrc);
      expect(assetRes.status()).toBe(200);
      const assetHeaders = assetRes.headers();
      expect(assetHeaders["x-content-type-options"]).toBe("nosniff");
      expect(assetHeaders["x-frame-options"]).toBe("DENY");
      expect(assetHeaders["referrer-policy"]).toBe("no-referrer");
      expect(assetHeaders["cache-control"]).toBe(
        "public, max-age=31536000, immutable"
      );
    }
  });

  test("theme anti-flash script executes and applies dark class before main render", async ({
    page,
  }) => {
    // Set dark theme in localStorage prior to document load
    await page.addInitScript(() => {
      localStorage.setItem("camera-monitor-theme", "dark");
    });

    await page.goto("/");
    const isDark = await page.evaluate(() =>
      document.documentElement.classList.contains("dark")
    );
    expect(isDark).toBe(true);
  });

  test("add-camera round trip directly against production single-process server", async ({
    page,
    request,
  }) => {
    await page.goto("/");
    await expect(page.getByTestId("empty-cameras-state")).toBeVisible();

    // Click Add Camera button
    await page.getByTestId("add-camera-toolbar-button").click();
    const formDialog = page.getByTestId("camera-form-dialog");
    await expect(formDialog).toBeVisible();

    await page.getByTestId("camera-name-input").fill("Prod Unit A");
    await page.getByTestId("camera-ip-input").fill("192.0.2.77");
    await page.getByTestId("camera-location-input").fill("Server Room");
    await page
      .getByTestId("camera-description-input")
      .fill("Production E2E verification camera");

    await page.getByTestId("submit-camera-form-button").click();
    await expect(formDialog).not.toBeVisible();

    // Verify row appeared in dashboard
    await expect(page.getByText("Prod Unit A")).toBeVisible();
    await expect(page.getByText("192.0.2.77")).toBeVisible();

    // Verify direct API call returns the camera
    const apiRes = await request.get(`${prodBaseUrl}/api/cameras`);
    expect(apiRes.status()).toBe(200);
    const cameras = await apiRes.json();
    expect(cameras).toHaveLength(1);
    expect(cameras[0].camera_name).toBe("Prod Unit A");
    expect(cameras[0].ip_address).toBe("192.0.2.77");
  });
});
