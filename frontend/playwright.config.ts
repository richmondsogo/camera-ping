import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(__dirname, "../backend");
const isWin = process.platform === "win32";
const pythonCmd = isWin
  ? path.join(backendDir, ".venv", "Scripts", "python.exe")
  : path.join(backendDir, ".venv", "bin", "python");

const repoRootDir = path.resolve(__dirname, "..");
const e2eBackendScript = path.join(repoRootDir, "scripts", "e2e_backend.py");
const e2eBackendPort = Number(process.env.E2E_BACKEND_PORT || "18000");
const e2eFrontendPort = Number(process.env.E2E_FRONTEND_PORT || "15173");
const e2eProdPort = Number(process.env.E2E_PROD_PORT || "18080");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 60 * 1000,
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : "list",
  use: {
    baseURL: `http://localhost:${e2eFrontendPort}`,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: /production\.spec\.ts/,
    },
    {
      name: "production",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: `http://127.0.0.1:${e2eProdPort}`,
      },
      testMatch: /production\.spec\.ts/,
    },
  ],
  webServer: [
    {
      command: `"${pythonCmd}" "${e2eBackendScript}"`,
      cwd: repoRootDir,
      port: e2eBackendPort,
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
    {
      command: `pnpm dev --port ${e2eFrontendPort} --strictPort`,
      cwd: __dirname,
      port: e2eFrontendPort,
      env: {
        API_PROXY_TARGET: `http://127.0.0.1:${e2eBackendPort}`,
        PORT: String(e2eFrontendPort),
      },
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
    {
      command: `"${pythonCmd}" -m app.serve`,
      cwd: backendDir,
      port: e2eProdPort,
      env: {
        DATABASE_URL: `sqlite:///${path.join(backendDir, ".e2e-data", "e2e_prod_cameras.db").replace(/\\/g, "/")}`,
        LOG_DIR: path.join(backendDir, ".e2e-data", "logs"),
        FRONTEND_DIST: path.join(__dirname, "dist"),
        BACKEND_PORT: String(e2eProdPort),
        BACKEND_HOST: "127.0.0.1",
      },
      reuseExistingServer: false,
      timeout: 120 * 1000,
    },
  ],
});
