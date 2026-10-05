import { describe, it, expect } from "vitest";
import {
  cameraFormSchema,
  cameraReadSchema,
  monitoringStatusSchema,
  settingsResponseSchema,
  settingsUpdateSchema,
} from "./schemas";
import vectors from "../../../shared/camera-validation-vectors.json";

describe("Camera Validation Parity with Shared Vectors", () => {
  for (const vector of vectors) {
    const {
      field,
      input,
      expected,
      expected_stored,
      expected_message,
      frontend_stricter,
    } = vector;

    it(`validates ${field} with input ${JSON.stringify(input)}`, () => {
      const fieldSchema =
        cameraFormSchema.shape[field as keyof typeof cameraFormSchema.shape];
      const result = fieldSchema.safeParse(input);

      if (frontend_stricter) {
        expect(result.success).toBe(false);
        return;
      }

      if (expected === "valid") {
        expect(result.success).toBe(true);
        if (result.success && expected_stored !== null) {
          expect(result.data).toBe(expected_stored);
        }
      } else {
        expect(result.success).toBe(false);
        if (!result.success && expected_message) {
          const messages = result.error.issues.map((i) => i.message);
          expect(messages).toContain(expected_message);
        }
      }
    });
  }
});

describe("CameraRead and MonitoringStatus Schema Validation", () => {
  it("validates CameraRead with consecutive_failures", () => {
    const raw = {
      id: 1,
      camera_name: "Cam 1",
      location: "Office",
      description: "Desk",
      ip_address: "192.0.2.1",
      status: "offline",
      consecutive_failures: 5,
      last_checked: "2026-10-01T12:00:00Z",
      last_online: "2026-10-01T10:00:00Z",
      created_at: "2026-10-01T08:00:00Z",
      updated_at: "2026-10-01T08:00:00Z",
    };
    const parsed = cameraReadSchema.safeParse(raw);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.consecutive_failures).toBe(5);
    }
  });

  it("validates MonitoringStatus with running_since and counts", () => {
    const raw = {
      running: true,
      interval_seconds: 60,
      running_since: "2026-10-01T12:00:00Z",
      last_cycle_started_at: "2026-10-01T12:01:00Z",
      last_cycle_finished_at: "2026-10-01T12:01:05Z",
      next_check_at: "2026-10-01T12:02:00Z",
      total: 10,
      online: 8,
      offline: 2,
      unknown: 0,
    };
    const parsed = monitoringStatusSchema.safeParse(raw);
    expect(parsed.success).toBe(true);
    if (parsed.success) {
      expect(parsed.data.running_since).toBe("2026-10-01T12:00:00Z");
      expect(parsed.data.total).toBe(10);
    }
  });

  it("validates settingsResponseSchema and settingsUpdateSchema bounds", () => {
    expect(
      settingsResponseSchema.safeParse({ check_interval_seconds: 60 }).success
    ).toBe(true);
    expect(
      settingsResponseSchema.safeParse({ check_interval_seconds: 10 }).success
    ).toBe(true);
    expect(
      settingsResponseSchema.safeParse({ check_interval_seconds: 31536000 })
        .success
    ).toBe(true);
    expect(
      settingsResponseSchema.safeParse({ check_interval_seconds: 9 }).success
    ).toBe(false);
    expect(
      settingsResponseSchema.safeParse({ check_interval_seconds: 31536001 })
        .success
    ).toBe(false);
    expect(
      settingsResponseSchema.safeParse({ check_interval_seconds: "60" }).success
    ).toBe(false);

    expect(
      settingsUpdateSchema.safeParse({ check_interval_seconds: 120 }).success
    ).toBe(true);
    expect(
      settingsUpdateSchema.safeParse({ check_interval_seconds: 5 }).success
    ).toBe(false);
  });
});
