import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const screenshotsDir = path.resolve(__dirname, "../screenshots");

if (!fs.existsSync(screenshotsDir)) {
  fs.mkdirSync(screenshotsDir, { recursive: true });
}

const routes = [
  { name: "dashboard", path: "/" },
  { name: "settings", path: "/settings" },
  { name: "design", path: "/_design" },
];

const baseUrl = process.env.BASE_URL || "http://localhost:5173";

async function main() {
  console.log(`Starting screenshot capture from ${baseUrl}...`);
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  const page = await context.newPage();

  for (const route of routes) {
    const url = `${baseUrl}${route.path}`;
    console.log(`Capturing ${route.name} (${url})...`);
    await page.goto(url, { waitUntil: "networkidle" });

    // Light mode shot
    await page.evaluate(() =>
      document.documentElement.classList.remove("dark")
    );
    const lightPath = path.join(screenshotsDir, `${route.name}-light.png`);
    await page.screenshot({ path: lightPath, fullPage: true });
    console.log(`  -> Saved ${lightPath}`);

    // Dark mode shot
    await page.evaluate(() => document.documentElement.classList.add("dark"));
    const darkPath = path.join(screenshotsDir, `${route.name}-dark.png`);
    await page.screenshot({ path: darkPath, fullPage: true });
    console.log(`  -> Saved ${darkPath}`);

    // Cleanup dark class
    await page.evaluate(() =>
      document.documentElement.classList.remove("dark")
    );
  }

  await browser.close();
  console.log("All screenshots captured successfully.");
}

main().catch((err) => {
  console.error("Screenshot capture failed:", err);
  process.exit(1);
});
