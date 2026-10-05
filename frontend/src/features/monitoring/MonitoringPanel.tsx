import * as React from "react";
import { Button } from "@/components/ui/button";
import { useNow } from "@/features/monitoring/useNow";
import {
  cycleInProgress,
  formatTime24h,
  isStalled,
  type StatusCounts,
} from "@/features/monitoring/utils";
import type { MonitoringStatus } from "@/lib/schemas";

export interface MonitoringPanelProps {
  status: MonitoringStatus | null | undefined;
  counts: StatusCounts;
  isStarting: boolean;
  isStopping: boolean;
  onStart: () => Promise<void> | void;
  onStop: () => Promise<void> | void;
  startError: boolean;
  stopError: boolean;
  isConnectionLost: boolean;
  lastSuccessTime: number | null;
}

export function MonitoringPanel({
  status,
  counts,
  isStarting,
  isStopping,
  onStart,
  onStop,
  startError,
  stopError,
  isConnectionLost,
  lastSuccessTime,
}: MonitoringPanelProps) {
  const isRunning = status?.running ?? false;
  const isPending = isStarting || isStopping;

  const startButtonRef = React.useRef<HTMLButtonElement | null>(null);
  const stopButtonRef = React.useRef<HTMLButtonElement | null>(null);

  const [announcement, setAnnouncement] = React.useState("");

  // Ticking clock updated every 1s for accurate stall and in-progress evaluation
  const now = useNow(1000);

  // Focus management per amendment 3
  const handleStart = React.useCallback(async () => {
    try {
      await onStart();
      setAnnouncement("Monitoring started.");
      requestAnimationFrame(() => {
        stopButtonRef.current?.focus();
      });
    } catch {
      requestAnimationFrame(() => {
        startButtonRef.current?.focus();
      });
    }
  }, [onStart]);

  const handleStop = React.useCallback(async () => {
    try {
      await onStop();
      setAnnouncement("Monitoring stopped.");
      requestAnimationFrame(() => {
        startButtonRef.current?.focus();
      });
    } catch {
      requestAnimationFrame(() => {
        stopButtonRef.current?.focus();
      });
    }
  }, [onStop]);

  // Derived display strings
  const inProgress = cycleInProgress(status);
  let lastCheckDisplay = "Never";
  if (inProgress) {
    lastCheckDisplay = "Checking now…";
  } else if (status?.last_cycle_finished_at) {
    const formatted = formatTime24h(status.last_cycle_finished_at);
    if (formatted) lastCheckDisplay = formatted;
  }

  const nextCheckDisplay =
    isRunning && status?.next_check_at
      ? (formatTime24h(status.next_check_at) ?? "—")
      : "—";

  const intervalDisplay = status?.interval_seconds ?? 60;

  // Stalled banner: per Amendment 2, suppressed while connection is lost
  const stalled = !isConnectionLost && isStalled(status, now);
  const stalledTime =
    status?.last_cycle_finished_at || status?.running_since
      ? formatTime24h(status.last_cycle_finished_at ?? status.running_since)
      : null;

  // All offline banner: when running, total >= 2, and offline === total
  const allOffline =
    isRunning && counts.total >= 2 && counts.offline === counts.total;

  return (
    <div className="flex flex-col gap-tight" data-testid="monitoring-section">
      {/* Screen Reader Live Region */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="monitoring-announcer"
      >
        {announcement}
      </div>

      {/* Main Monitoring Panel */}
      <div
        data-testid="monitoring-panel"
        className="rounded-control border border-border bg-background p-panel-pad"
      >
        <div className="flex flex-wrap items-center justify-between gap-inline gap-y-tight">
          {/* Left Group: Running/Stopped status + Counts */}
          <div className="flex flex-wrap items-center gap-inline">
            {/* Running state indicator */}
            <div className="flex items-center gap-tight whitespace-nowrap">
              <span
                data-slot="monitoring-dot"
                className={`size-2 shrink-0 rounded-full ${
                  isRunning ? "bg-status-online" : "bg-status-unknown"
                }`}
                aria-hidden="true"
              />
              <span
                data-slot="monitoring-state"
                className="text-sm font-medium text-foreground"
              >
                {isRunning ? "Monitoring running" : "Monitoring stopped"}
              </span>
            </div>

            {/* Counts (derived from camera list) */}
            <div
              className="flex items-center gap-tight text-sm tabular-nums text-muted-foreground"
              data-testid="monitoring-counts"
            >
              {counts.total > 0 && (
                <span className="text-foreground">
                  {counts.total} {counts.total === 1 ? "camera" : "cameras"}
                </span>
              )}
              {counts.online > 0 && <span>{counts.online} online</span>}
              {counts.offline > 0 && <span>{counts.offline} offline</span>}
              {counts.unknown > 0 && <span>{counts.unknown} unknown</span>}
            </div>
          </div>

          {/* Right Group: Timings + Actions */}
          <div className="flex flex-wrap items-center gap-inline">
            <div
              className="flex flex-wrap items-center gap-tight text-xs text-muted-foreground tabular-nums"
              data-testid="monitoring-timings"
            >
              <span data-testid="last-check">
                Last check {lastCheckDisplay}
              </span>
              <span aria-hidden="true">·</span>
              <span data-testid="next-check">
                Next check {nextCheckDisplay}
              </span>
              <span aria-hidden="true">·</span>
              <span data-testid="check-interval">
                Checks every {intervalDisplay} seconds
              </span>
            </div>

            {/* Start and Stop Buttons */}
            <div className="flex items-center gap-tight">
              <Button
                ref={startButtonRef}
                variant="default"
                size="sm"
                onClick={() => void handleStart()}
                disabled={isRunning || isPending}
                data-testid="start-monitoring-button"
                aria-label="Start monitoring"
              >
                Start
              </Button>
              <Button
                ref={stopButtonRef}
                variant="outline"
                size="sm"
                onClick={() => void handleStop()}
                disabled={!isRunning || isPending}
                data-testid="stop-monitoring-button"
                aria-label="Stop monitoring"
              >
                Stop
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Start / Stop Inline Alert */}
      {startError && (
        <p
          role="alert"
          className="text-xs text-error"
          data-testid="start-error-alert"
        >
          Couldn't start monitoring. Try again.
        </p>
      )}
      {stopError && (
        <p
          role="alert"
          className="text-xs text-error"
          data-testid="stop-error-alert"
        >
          Couldn't stop monitoring. Try again.
        </p>
      )}

      {/* Stopped Notice */}
      {!isRunning && counts.total > 0 && (
        <p
          className="text-xs text-muted-foreground"
          data-testid="stopped-notice"
        >
          Monitoring is stopped. Statuses below are from the last check.
        </p>
      )}

      {/* Connection Lost Banner */}
      {isConnectionLost && (
        <div
          role="alert"
          data-testid="connection-lost-banner"
          className="rounded-control border border-error bg-background p-control-x text-sm text-error"
        >
          Can't reach the server. Showing data from{" "}
          {lastSuccessTime ? (formatTime24h(lastSuccessTime) ?? "—") : "—"}.
          Retrying…
        </div>
      )}

      {/* Stalled Banner */}
      {stalled && (
        <div
          role="alert"
          data-testid="stalled-banner"
          className="rounded-control border border-error bg-background p-control-x text-sm text-error"
        >
          Monitoring looks stalled: no completed check since{" "}
          {stalledTime ?? "—"}.
        </div>
      )}

      {/* All Offline Banner */}
      {allOffline && (
        <div
          role="status"
          data-testid="all-offline-banner"
          className="rounded-control border border-border bg-muted p-control-x text-sm text-muted-foreground"
        >
          Every camera is offline. If that's unexpected, check this PC's network
          connection.
        </div>
      )}
    </div>
  );
}
