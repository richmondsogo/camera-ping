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

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
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
  ],
});
