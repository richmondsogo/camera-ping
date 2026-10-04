import { describe, expect, it } from "vitest";
import type { CameraRead, MonitoringStatus } from "@/lib/schemas";
import {
  countByStatus,
  cycleInProgress,
  formatCheckCount,
  formatTime24h,
  isStalled,
} from "./utils";

describe("Monitoring Utilities", () => {
  describe("countByStatus", () => {
    it("returns all zeros for empty cameras array", () => {
      expect(countByStatus([])).toEqual({
        total: 0,
        online: 0,
        offline: 0,
        unknown: 0,
      });
    });

    it("correctly partitions cameras by status", () => {
      const mockCameras: CameraRead[] = [
        {
          id: 1,
          camera_name: "Cam 1",
          location: "Gate",
          description: "Desc",
          ip_address: "192.0.2.1",
          status: "online",
          consecutive_failures: 0,
          last_checked: null,
          last_online: null,
          created_at: "2026-10-01T00:00:00Z",
          updated_at: "2026-10-01T00:00:00Z",
        },
        {
          id: 2,
          camera_name: "Cam 2",
          location: "Gate",
          description: "Desc",
          ip_address: "192.0.2.2",
          status: "offline",
          consecutive_failures: 3,
          last_checked: null,
          last_online: null,
          created_at: "2026-10-01T00:00:00Z",
          updated_at: "2026-10-01T00:00:00Z",
        },
        {
          id: 3,
          camera_name: "Cam 3",
          location: "Gate",
          description: "Desc",
          ip_address: "192.0.2.3",
          status: "offline",
          consecutive_failures: 1,
          last_checked: null,
          last_online: null,
          created_at: "2026-10-01T00:00:00Z",
          updated_at: "2026-10-01T00:00:00Z",
        },
        {
          id: 4,
          camera_name: "Cam 4",
          location: "Gate",
          description: "Desc",
          ip_address: "192.0.2.4",
          status: "unknown",
          consecutive_failures: 0,
          last_checked: null,
          last_online: null,
          created_at: "2026-10-01T00:00:00Z",
          updated_at: "2026-10-01T00:00:00Z",
        },
      ];

      expect(countByStatus(mockCameras)).toEqual({
        total: 4,
        online: 1,
        offline: 2,
        unknown: 1,
      });
    });
  });

  describe("formatCheckCount", () => {
    it("returns empty string for 0 or negative", () => {
      expect(formatCheckCount(0)).toBe("");
      expect(formatCheckCount(-1)).toBe("");
    });

    it("returns singular for 1 check", () => {
      expect(formatCheckCount(1)).toBe("1 check");
    });

    it("returns plural for counts between 2 and 98", () => {
      expect(formatCheckCount(2)).toBe("2 checks");
      expect(formatCheckCount(15)).toBe("15 checks");
      expect(formatCheckCount(98)).toBe("98 checks");
    });

    it("caps at 99+ checks for 99 and above", () => {
      expect(formatCheckCount(99)).toBe("99+ checks");
      expect(formatCheckCount(100)).toBe("99+ checks");
      expect(formatCheckCount(5000)).toBe("99+ checks");
    });
  });

  describe("cycleInProgress", () => {
    const baseStatus: MonitoringStatus = {
      running: true,
      interval_seconds: 60,
      running_since: "2026-10-01T10:00:00Z",
      last_cycle_started_at: null,
      last_cycle_finished_at: null,
      next_check_at: null,
      total: 0,
      online: 0,
      offline: 0,
      unknown: 0,
    };

    it("returns false if status is null or not running", () => {
      expect(cycleInProgress(null)).toBe(false);
      expect(cycleInProgress({ ...baseStatus, running: false })).toBe(false);
    });

    it("returns false if last_cycle_started_at is null", () => {
      expect(cycleInProgress(baseStatus)).toBe(false);
    });

    it("returns true if started is set but finished is null", () => {
      expect(
        cycleInProgress({
          ...baseStatus,
          last_cycle_started_at: "2026-10-01T10:00:00Z",
          last_cycle_finished_at: null,
        })
      ).toBe(true);
    });

    it("returns true when started is more recent than finished", () => {
      expect(
        cycleInProgress({
          ...baseStatus,
          last_cycle_started_at: "2026-10-01T10:01:00Z",
          last_cycle_finished_at: "2026-10-01T10:00:30Z",
        })
      ).toBe(true);
    });

    it("returns false when cycle has finished", () => {
      expect(
        cycleInProgress({
          ...baseStatus,
          last_cycle_started_at: "2026-10-01T10:01:00Z",
          last_cycle_finished_at: "2026-10-01T10:01:05Z",
        })
      ).toBe(false);
    });
  });

  describe("isStalled", () => {
    const startIso = "2026-10-01T12:00:00.000Z";
    const startMs = new Date(startIso).getTime();

    const baseStatus: MonitoringStatus = {
      running: true,
      interval_seconds: 60,
      running_since: startIso,
      last_cycle_started_at: null,
      last_cycle_finished_at: null,
      next_check_at: null,
      total: 10,
      online: 8,
      offline: 2,
      unknown: 0,
    };

    it("returns false when status is null, undefined, or stopped", () => {
      expect(isStalled(null, startMs + 100000)).toBe(false);
      expect(isStalled(undefined, startMs + 100000)).toBe(false);
      expect(
        isStalled({ ...baseStatus, running: false }, startMs + 1000000)
      ).toBe(false);
    });

    it("right after start with no finished cycle: uses running_since as reference", () => {
      // interval = 60s -> threshold = max(3 * 60, 30) = 180s = 180,000ms
      // 179s elapsed -> false
      expect(isStalled(baseStatus, startMs + 179_000)).toBe(false);
      // Exactly 180s elapsed -> false
      expect(isStalled(baseStatus, startMs + 180_000)).toBe(false);
      // 181s elapsed -> true
      expect(isStalled(baseStatus, startMs + 181_000)).toBe(true);
    });

    it("does not report stalled right after start even if DB had an old finished cycle from hours ago", () => {
      const oldFinishedIso = "2026-10-01T08:00:00.000Z"; // 4 hours before start
      const statusWithOldFinished: MonitoringStatus = {
        ...baseStatus,
        last_cycle_finished_at: oldFinishedIso,
      };

      // Reference is max(12:00, 08:00) = 12:00 (running_since)
      // At 12:01 (60s after start) -> NOT stalled
      expect(isStalled(statusWithOldFinished, startMs + 60_000)).toBe(false);
      // At 12:03:01 (181s after start) -> stalled
      expect(isStalled(statusWithOldFinished, startMs + 181_000)).toBe(true);
    });

    it("when cycles have completed: uses last_cycle_finished_at if after running_since", () => {
      const finishedIso = "2026-10-01T12:05:00.000Z";
      const finishedMs = new Date(finishedIso).getTime();
      const statusWithRecentFinished: MonitoringStatus = {
        ...baseStatus,
        last_cycle_finished_at: finishedIso,
      };

      // Reference is 12:05:00
      // 179s after 12:05:00 -> false
      expect(isStalled(statusWithRecentFinished, finishedMs + 179_000)).toBe(
        false
      );
      // 181s after 12:05:00 -> true
      expect(isStalled(statusWithRecentFinished, finishedMs + 181_000)).toBe(
        true
      );
    });

    it("respects minimum 30-second threshold for short check intervals", () => {
      const shortIntervalStatus: MonitoringStatus = {
        ...baseStatus,
        interval_seconds: 5, // 3 * 5 = 15s < 30s min -> threshold is 30s
      };

      // 25s elapsed -> false
      expect(isStalled(shortIntervalStatus, startMs + 25_000)).toBe(false);
      // 31s elapsed -> true
      expect(isStalled(shortIntervalStatus, startMs + 31_000)).toBe(true);
    });
  });

  describe("formatTime24h", () => {
    it("returns null for empty/invalid values", () => {
      expect(formatTime24h(null)).toBeNull();
      expect(formatTime24h(undefined)).toBeNull();
      expect(formatTime24h("invalid-date")).toBeNull();
    });

    it("formats ISO string into local HH:MM:SS", () => {
      const d = new Date(2026, 9, 1, 14, 5, 9);
      const res = formatTime24h(d.toISOString());
      expect(res).toBe("14:05:09");
    });
  });
});
