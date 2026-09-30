import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const targetSubdir = process.env.SCREENSHOTS_SUBDIR || process.argv[2] || "";
const screenshotsDir = targetSubdir
  ? path.resolve(__dirname, "../screenshots", targetSubdir)
  : path.resolve(__dirname, "../screenshots");

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

const baseUrl = process.env.BASE_URL || "http://localhost:5173";

const routes = [
  { name: "dashboard", path: "/" },
  { name: "settings", path: "/settings" },
  { name: "design", path: "/_design" },
];

async function applyStaticStyles(page) {
  await page.addInitScript(() => {
    const style = document.createElement("style");
    style.id = "disable-transitions-animations";
    style.textContent = `
      *, *::before, *::after {
        transition: none !important;
        animation: none !important;
      }
    `;
    if (document.head) {
      document.head.appendChild(style);
    } else {
      document.addEventListener("DOMContentLoaded", () => {
        document.head.appendChild(style);
      });
    }
  });
}

async function settlePage(page) {
  await page.waitForLoadState("networkidle");
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(200);
}

async function setTheme(page, isDark, isDesignRoute = false) {
  if (isDesignRoute) {
    const toggleBtn = page.locator('[data-testid="theme-toggle-button"]');
    const isCurrentlyDark = await page.evaluate(() =>
      document.documentElement.classList.contains("dark")
    );
    if (isCurrentlyDark !== isDark) {
      await toggleBtn.click();
    }
  } else {
    if (isDark) {
      await page.evaluate(() => document.documentElement.classList.add("dark"));
    } else {
      await page.evaluate(() =>
        document.documentElement.classList.remove("dark")
      );
    }
  }
  await settlePage(page);
}

async function captureRoute(page, route) {
  const url = `${baseUrl}${route.path}`;
  console.log(`Capturing ${route.name} (${url})...`);
  await page.goto(url, { waitUntil: "networkidle" });

  const isDesign = route.path === "/_design";

  // 1. Light mode full page
  await setTheme(page, false, isDesign);
  const lightPath = path.join(screenshotsDir, `${route.name}-light.png`);
  await page.screenshot({ path: lightPath, fullPage: true });
  console.log(`  -> Saved ${lightPath}`);

  // 2. Dark mode full page
  await setTheme(page, true, isDesign);
  const darkPath = path.join(screenshotsDir, `${route.name}-dark.png`);
  await page.screenshot({ path: darkPath, fullPage: true });
  console.log(`  -> Saved ${darkPath}`);

  // Reset to light
  await setTheme(page, false, isDesign);
}

async function captureInteractiveStates(page) {
  const url = `${baseUrl}/_design`;
  console.log(`Capturing interactive states on ${url}...`);

  for (const isDark of [false, true]) {
    const mode = isDark ? "dark" : "light";
    await page.goto(url, { waitUntil: "networkidle" });
    await setTheme(page, isDark, true);

    // State A: Select popup OPEN
    console.log(`  Capturing select-open (${mode})...`);
    const selectTrigger = page.locator('[data-testid="select-default"]');
    await selectTrigger.click();
    const selectPopup = page.locator('[data-slot="select-content"]');
    await selectPopup.waitFor({ state: "visible", timeout: 5000 });
    await page.waitForTimeout(200);

    const selectPath = path.join(screenshotsDir, `select-open-${mode}.png`);
    await page.screenshot({ path: selectPath, fullPage: false });
    console.log(`    -> Saved ${selectPath}`);

    // Close select popup
    await page.keyboard.press("Escape");
    await selectPopup.waitFor({ state: "hidden", timeout: 5000 });
    await page.waitForTimeout(100);

    // State B: Dialog OPEN
    console.log(`  Capturing dialog-open (${mode})...`);
    const dialogTrigger = page.locator('[data-testid="dialog-trigger-button"]');
    await dialogTrigger.click();
    const dialogContent = page.locator('[data-testid="dialog-content-box"]');
    await dialogContent.waitFor({ state: "visible", timeout: 5000 });
    await page.waitForTimeout(200);

    const dialogPath = path.join(screenshotsDir, `dialog-open-${mode}.png`);
    await page.screenshot({ path: dialogPath, fullPage: false });
    console.log(`    -> Saved ${dialogPath}`);

    // Close dialog
    await page.keyboard.press("Escape");
    await dialogContent.waitFor({ state: "hidden", timeout: 5000 });
    await page.waitForTimeout(100);

    // State C: Keyboard-focused button
    console.log(`  Capturing button-focused (${mode})...`);
    const defaultButton = page.locator('[data-testid="button-default"]');
    await defaultButton.focus();
    await page.waitForTimeout(200);

    const buttonPath = path.join(screenshotsDir, `button-focused-${mode}.png`);
    await page.screenshot({ path: buttonPath, fullPage: false });
    console.log(`    -> Saved ${buttonPath}`);
  }
}

async function main() {
  console.log(
    `Starting screenshot capture from ${baseUrl} into ${screenshotsDir}...`
  );
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();

  // Enforce zero transition/animation on every navigation
  await applyStaticStyles(page);

  // Capture basic routes
  for (const route of routes) {
    await captureRoute(page, route);
  }

  // Capture interactive states on /_design
  await captureInteractiveStates(page);

  await browser.close();
  console.log("All screenshots captured successfully.");
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
