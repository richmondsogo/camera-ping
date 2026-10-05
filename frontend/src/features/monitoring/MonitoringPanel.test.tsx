import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  MonitoringPanel,
  type MonitoringPanelProps,
} from "@/features/monitoring/MonitoringPanel";
import type { MonitoringStatus } from "@/lib/schemas";

const defaultProps: MonitoringPanelProps = {
  status: {
    running: false,
    interval_seconds: 60,
    last_cycle_started_at: null,
    last_cycle_finished_at: null,
    next_check_at: null,
    running_since: null,
    total: 3,
    online: 2,
    offline: 1,
    unknown: 0,
  },
  counts: { total: 3, online: 2, offline: 1, unknown: 0 },
  isStarting: false,
  isStopping: false,
  onStart: vi.fn(),
  onStop: vi.fn(),
  startError: false,
  stopError: false,
  isConnectionLost: false,
  lastSuccessTime: null,
};

describe("MonitoringPanel component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders stopped state with counts, 'Never' last check, and stopped notice", () => {
    render(<MonitoringPanel {...defaultProps} />);

    expect(screen.getByText("Monitoring stopped")).toBeInTheDocument();
    expect(screen.getByTestId("start-monitoring-button")).toBeEnabled();
    expect(screen.getByTestId("stop-monitoring-button")).toBeDisabled();

    expect(screen.getByTestId("monitoring-counts")).toHaveTextContent(
      "3 cameras"
    );
    expect(screen.getByTestId("monitoring-counts")).toHaveTextContent(
      "2 online"
    );
    expect(screen.getByTestId("monitoring-counts")).toHaveTextContent(
      "1 offline"
    );

    expect(screen.getByTestId("last-check")).toHaveTextContent(
      "Last check Never"
    );
    expect(screen.getByTestId("next-check")).toHaveTextContent("Next check —");
    expect(screen.getByTestId("check-interval")).toHaveTextContent(
      "Checks every 1 minute"
    );

    expect(screen.getByTestId("stopped-notice")).toHaveTextContent(
      "Monitoring is stopped. Statuses below are from the last check."
    );
  });

  it("renders running state with timings and no stopped notice", () => {
    const runningStatus: MonitoringStatus = {
      running: true,
      interval_seconds: 60,
      last_cycle_started_at: "2026-10-04T14:30:00Z",
      last_cycle_finished_at: "2026-10-04T14:30:02Z",
      next_check_at: "2026-10-04T14:31:00Z",
      running_since: "2026-10-04T14:00:00Z",
      total: 3,
      online: 2,
      offline: 1,
      unknown: 0,
    };

    render(<MonitoringPanel {...defaultProps} status={runningStatus} />);

    expect(screen.getByText("Monitoring running")).toBeInTheDocument();
    expect(screen.getByTestId("start-monitoring-button")).toBeDisabled();
    expect(screen.getByTestId("stop-monitoring-button")).toBeEnabled();

    expect(screen.getByTestId("last-check")).not.toHaveTextContent("Never");
    expect(screen.getByTestId("next-check")).not.toHaveTextContent("—");
    expect(screen.queryByTestId("stopped-notice")).not.toBeInTheDocument();
  });

  it("displays 'Checking now…' when cycle is in progress", () => {
    const inProgressStatus: MonitoringStatus = {
      running: true,
      interval_seconds: 60,
      last_cycle_started_at: "2026-10-04T14:30:00Z",
      last_cycle_finished_at: null,
      next_check_at: null,
      running_since: "2026-10-04T14:29:50Z",
      total: 3,
      online: 2,
      offline: 1,
      unknown: 0,
    };

    render(<MonitoringPanel {...defaultProps} status={inProgressStatus} />);

    expect(screen.getByTestId("last-check")).toHaveTextContent(
      "Last check Checking now…"
    );
  });

  it("disables both buttons during start and stop mutations", () => {
    const { rerender } = render(
      <MonitoringPanel {...defaultProps} isStarting={true} />
    );
    expect(screen.getByTestId("start-monitoring-button")).toBeDisabled();
    expect(screen.getByTestId("stop-monitoring-button")).toBeDisabled();

    rerender(
      <MonitoringPanel
        {...defaultProps}
        status={{ ...defaultProps.status!, running: true }}
        isStopping={true}
      />
    );
    expect(screen.getByTestId("start-monitoring-button")).toBeDisabled();
    expect(screen.getByTestId("stop-monitoring-button")).toBeDisabled();
  });

  it("shows inline alert messages for start and stop errors", () => {
    const { rerender } = render(
      <MonitoringPanel {...defaultProps} startError={true} />
    );
    expect(screen.getByTestId("start-error-alert")).toHaveTextContent(
      "Couldn't start monitoring. Try again."
    );

    rerender(<MonitoringPanel {...defaultProps} stopError={true} />);
    expect(screen.getByTestId("stop-error-alert")).toHaveTextContent(
      "Couldn't stop monitoring. Try again."
    );
  });

  describe("Focus management (Amendment 3)", () => {
    it("moves focus to Stop button after successful Start", async () => {
      const onStart = vi.fn().mockResolvedValue(undefined);
      render(<MonitoringPanel {...defaultProps} onStart={onStart} />);

      const startBtn = screen.getByTestId("start-monitoring-button");
      const stopBtn = screen.getByTestId("stop-monitoring-button");

      startBtn.focus();
      expect(document.activeElement).toBe(startBtn);

      fireEvent.click(startBtn);

      await act(async () => {
        await Promise.resolve();
        await new Promise((r) => requestAnimationFrame(r));
      });

      expect(document.activeElement).toBe(stopBtn);
      expect(document.activeElement).not.toBe(document.body);
    });

    it("moves focus to Start button after successful Stop", async () => {
      const onStop = vi.fn().mockResolvedValue(undefined);
      render(
        <MonitoringPanel
          {...defaultProps}
          status={{ ...defaultProps.status!, running: true }}
          onStop={onStop}
        />
      );

      const startBtn = screen.getByTestId("start-monitoring-button");
      const stopBtn = screen.getByTestId("stop-monitoring-button");

      stopBtn.focus();
      expect(document.activeElement).toBe(stopBtn);

      fireEvent.click(stopBtn);

      await act(async () => {
        await Promise.resolve();
        await new Promise((r) => requestAnimationFrame(r));
      });

      expect(document.activeElement).toBe(startBtn);
      expect(document.activeElement).not.toBe(document.body);
    });

    it("keeps focus on Start button when Start request fails", async () => {
      const onStart = vi.fn().mockRejectedValue(new Error("Network failed"));
      render(<MonitoringPanel {...defaultProps} onStart={onStart} />);

      const startBtn = screen.getByTestId("start-monitoring-button");
      startBtn.focus();
      expect(document.activeElement).toBe(startBtn);

      fireEvent.click(startBtn);

      await act(async () => {
        await Promise.resolve();
        await new Promise((r) => requestAnimationFrame(r));
      });

      expect(document.activeElement).toBe(startBtn);
      expect(document.activeElement).not.toBe(document.body);
    });

    it("keeps focus on Stop button when Stop request fails", async () => {
      const onStop = vi.fn().mockRejectedValue(new Error("Network failed"));
      render(
        <MonitoringPanel
          {...defaultProps}
          status={{ ...defaultProps.status!, running: true }}
          onStop={onStop}
        />
      );

      const stopBtn = screen.getByTestId("stop-monitoring-button");
      stopBtn.focus();
      expect(document.activeElement).toBe(stopBtn);

      fireEvent.click(stopBtn);

      await act(async () => {
        await Promise.resolve();
        await new Promise((r) => requestAnimationFrame(r));
      });

      expect(document.activeElement).toBe(stopBtn);
      expect(document.activeElement).not.toBe(document.body);
    });
  });

  describe("Ticking clock stall detection (Amendment 1)", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("shows stalled banner once threshold passes WITHOUT any new data arriving, and is absent just before", () => {
      const baseTime = new Date("2026-10-04T12:00:00Z").getTime();
      vi.setSystemTime(baseTime);

      // interval is 10s -> threshold is max(3 * 10, 30) = 30s
      // Finished 25 seconds ago (25s elapsed)
      const finishedAt = new Date(baseTime - 25 * 1000).toISOString();
      const frozenStatus: MonitoringStatus = {
        running: true,
        interval_seconds: 10,
        last_cycle_started_at: new Date(baseTime - 26 * 1000).toISOString(),
        last_cycle_finished_at: finishedAt,
        next_check_at: new Date(baseTime - 15 * 1000).toISOString(),
        running_since: new Date(baseTime - 100 * 1000).toISOString(),
        total: 3,
        online: 2,
        offline: 1,
        unknown: 0,
      };

      render(<MonitoringPanel {...defaultProps} status={frozenStatus} />);

      // At 25s elapsed, threshold is 30s: stalled banner is NOT present
      expect(screen.queryByTestId("stalled-banner")).not.toBeInTheDocument();

      // Advance by 4 seconds (29s elapsed, just before 30s threshold)
      act(() => {
        vi.advanceTimersByTime(4 * 1000);
      });
      expect(screen.queryByTestId("stalled-banner")).not.toBeInTheDocument();

      // Advance by 2 more seconds (31s elapsed, past 30s threshold)
      act(() => {
        vi.advanceTimersByTime(2 * 1000);
      });

      // Stalled banner appears without any new props or query updates!
      expect(screen.getByTestId("stalled-banner")).toBeInTheDocument();
      expect(screen.getByTestId("stalled-banner")).toHaveTextContent(
        "Monitoring looks stalled: no completed check since"
      );
    });
  });

  describe("Connection lost & stall suppression (Amendment 2)", () => {
    it("suppresses stalled banner while connection lost banner is active", () => {
      // Elapsed 200s (way past threshold)
      const frozenStatus: MonitoringStatus = {
        running: true,
        interval_seconds: 60,
        last_cycle_started_at: "2026-10-04T12:00:00Z",
        last_cycle_finished_at: "2026-10-04T12:00:02Z",
        next_check_at: "2026-10-04T12:01:00Z",
        running_since: "2026-10-04T11:00:00Z",
        total: 3,
        online: 2,
        offline: 1,
        unknown: 0,
      };

      const { rerender } = render(
        <MonitoringPanel
          {...defaultProps}
          status={frozenStatus}
          isConnectionLost={true}
          lastSuccessTime={new Date("2026-10-04T12:00:02Z").getTime()}
        />
      );

      // Connection banner shown
      expect(screen.getByTestId("connection-lost-banner")).toBeInTheDocument();
      expect(screen.getByTestId("connection-lost-banner")).toHaveTextContent(
        "Can't reach the server. Showing data from"
      );

      // Stalled banner MUST NOT be shown
      expect(screen.queryByTestId("stalled-banner")).not.toBeInTheDocument();

      // After recovery (isConnectionLost becomes false)
      rerender(
        <MonitoringPanel
          {...defaultProps}
          status={frozenStatus}
          isConnectionLost={false}
          lastSuccessTime={new Date("2026-10-04T12:00:02Z").getTime()}
        />
      );

      expect(
        screen.queryByTestId("connection-lost-banner")
      ).not.toBeInTheDocument();
      expect(screen.getByTestId("stalled-banner")).toBeInTheDocument();
    });
  });

  describe("All-offline banner", () => {
    it("shows all-offline banner when running, total >= 2, and all cameras offline", () => {
      const runningStatus: MonitoringStatus = {
        running: true,
        interval_seconds: 60,
        last_cycle_started_at: "2026-10-04T12:00:00Z",
        last_cycle_finished_at: "2026-10-04T12:00:02Z",
        next_check_at: "2026-10-04T12:01:00Z",
        running_since: "2026-10-04T11:00:00Z",
        total: 3,
        online: 0,
        offline: 3,
        unknown: 0,
      };

      const { rerender } = render(
        <MonitoringPanel
          {...defaultProps}
          status={runningStatus}
          counts={{ total: 3, online: 0, offline: 3, unknown: 0 }}
        />
      );

      expect(screen.getByTestId("all-offline-banner")).toHaveTextContent(
        "Every camera is offline. If that's unexpected, check this PC's network connection."
      );

      // Not shown if not all offline
      rerender(
        <MonitoringPanel
          {...defaultProps}
          status={runningStatus}
          counts={{ total: 3, online: 1, offline: 2, unknown: 0 }}
        />
      );
      expect(
        screen.queryByTestId("all-offline-banner")
      ).not.toBeInTheDocument();

      // Not shown if total < 2
      rerender(
        <MonitoringPanel
          {...defaultProps}
          status={runningStatus}
          counts={{ total: 1, online: 0, offline: 1, unknown: 0 }}
        />
      );
      expect(
        screen.queryByTestId("all-offline-banner")
      ).not.toBeInTheDocument();

      // Not shown if stopped
      rerender(
        <MonitoringPanel
          {...defaultProps}
          status={{ ...runningStatus, running: false }}
          counts={{ total: 3, online: 0, offline: 3, unknown: 0 }}
        />
      );
      expect(
        screen.queryByTestId("all-offline-banner")
      ).not.toBeInTheDocument();
    });
  });
});
