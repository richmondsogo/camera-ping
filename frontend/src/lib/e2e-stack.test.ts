import { describe, it, expect, vi, afterEach } from "vitest";
import {
  assertE2eStack,
  DEFAULT_E2E_BACKEND_PORT,
  resetCameras,
  resetSettings,
  seedCameras,
} from "./e2e-stack";

describe("assertE2eStack", () => {
  const originalEnv = process.env.E2E_BACKEND_PORT;

  afterEach(() => {
    if (originalEnv === undefined) {
      delete process.env.E2E_BACKEND_PORT;
    } else {
      process.env.E2E_BACKEND_PORT = originalEnv;
    }
    vi.restoreAllMocks();
  });

  it("throws when called with protected dev backend port 8000", () => {
    expect(() => assertE2eStack(8000)).toThrow(
      /protected production\/development port 8000/
    );
    expect(() => assertE2eStack("http://127.0.0.1:8000")).toThrow(
      /protected production\/development port 8000/
    );
    expect(() => assertE2eStack("http://localhost:8000/api/cameras")).toThrow(
      /protected production\/development port 8000/
    );
  });

  it("throws when called with protected dev frontend port 5173", () => {
    expect(() => assertE2eStack(5173)).toThrow(
      /protected production\/development port 5173/
    );
    expect(() => assertE2eStack("http://localhost:5173")).toThrow(
      /protected production\/development port 5173/
    );
  });

  it("throws when called with an arbitrary non-e2e port", () => {
    expect(() => assertE2eStack(3000)).toThrow(
      /does not match configured e2e backend port 18000/
    );
    expect(() => assertE2eStack("http://127.0.0.1:15173")).toThrow(
      /does not match configured e2e backend port 18000/
    );
  });

  it("succeeds when called with the default e2e backend port 18000", () => {
    expect(() => assertE2eStack(DEFAULT_E2E_BACKEND_PORT)).not.toThrow();
    expect(() => assertE2eStack("http://127.0.0.1:18000")).not.toThrow();
    expect(() => assertE2eStack("http://localhost:18000/api")).not.toThrow();
  });

  it("respects custom E2E_BACKEND_PORT environment variable", () => {
    process.env.E2E_BACKEND_PORT = "19000";
    expect(() => assertE2eStack(18000)).toThrow(
      /does not match configured e2e backend port 19000/
    );
    expect(() => assertE2eStack(19000)).not.toThrow();
    expect(() => assertE2eStack("http://127.0.0.1:19000")).not.toThrow();
  });

  it("guards resetCameras from executing against port 8000", async () => {
    await expect(resetCameras("http://127.0.0.1:8000")).rejects.toThrow(
      /protected production\/development port 8000/
    );
  });

  it("guards seedCameras from executing against port 5173", async () => {
    await expect(seedCameras(5, "http://127.0.0.1:5173")).rejects.toThrow(
      /protected production\/development port 5173/
    );
  });

  it("guards resetSettings from executing against port 8000", async () => {
    await expect(resetSettings(60, "http://127.0.0.1:8000")).rejects.toThrow(
      /protected production\/development port 8000/
    );
  });
});
