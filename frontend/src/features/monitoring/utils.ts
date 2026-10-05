import type { CameraRead, MonitoringStatus } from "@/lib/schemas";

export interface StatusCounts {
  total: number;
  online: number;
  offline: number;
  unknown: number;
}

/**
 * Derive reachability summary counts from the active camera list.
 * This guarantees the monitoring summary panel and camera table always agree.
 */
export function countByStatus(cameras: CameraRead[]): StatusCounts {
  let online = 0;
  let offline = 0;
  let unknown = 0;

  for (const camera of cameras) {
    if (camera.status === "online") {
      online += 1;
    } else if (camera.status === "offline") {
      offline += 1;
    } else {
      unknown += 1;
    }
  }

  return {
    total: cameras.length,
    online,
    offline,
    unknown,
  };
}

/**
 * Check whether monitoring appears stalled.
 * Criteria: running AND nowMs - max(running_since, last_cycle_finished_at) > max(3 * interval_seconds, 30) seconds.
 * A null last_cycle_finished_at counts as -Infinity (so right after Start, reference is running_since).
 */
export function isStalled(
  status: MonitoringStatus | null | undefined,
  nowMs: number
): boolean {
  if (!status || !status.running || !status.running_since) {
    return false;
  }

  const runningSinceMs = new Date(status.running_since).getTime();
  if (Number.isNaN(runningSinceMs)) {
    return false;
  }

  const finishedMs = status.last_cycle_finished_at
    ? new Date(status.last_cycle_finished_at).getTime()
    : -Infinity;

  const validFinishedMs = Number.isNaN(finishedMs) ? -Infinity : finishedMs;
  const referenceMs = Math.max(runningSinceMs, validFinishedMs);
  const elapsedMs = nowMs - referenceMs;
  const thresholdMs = Math.max(3 * status.interval_seconds, 30) * 1000;

  return elapsedMs > thresholdMs;
}

/**
 * Format consecutive check failure count.
 * Returns: "1 check", "2 checks", ..., "99+ checks".
 */
export function formatCheckCount(n: number): string {
  if (n <= 0) return "";
  if (n === 1) return "1 check";
  if (n >= 99) return "99+ checks";
  return `${n} checks`;
}

/**
 * Check if a monitoring cycle is currently executing.
 * started > finished and running.
 */
export function cycleInProgress(
  status: MonitoringStatus | null | undefined
): boolean {
  if (!status || !status.running || !status.last_cycle_started_at) {
    return false;
  }

  const startedMs = new Date(status.last_cycle_started_at).getTime();
  if (Number.isNaN(startedMs)) {
    return false;
  }

  if (!status.last_cycle_finished_at) {
    return true;
  }

  const finishedMs = new Date(status.last_cycle_finished_at).getTime();
  if (Number.isNaN(finishedMs)) {
    return true;
  }

  return startedMs > finishedMs;
}

/**
 * Format an ISO UTC timestamp into a 24-hour local HH:MM:SS string.
 */
export function formatTime24h(
  dateOrIso: string | Date | number | null | undefined
): string | null {
  if (!dateOrIso) return null;
  const d = typeof dateOrIso === "object" ? dateOrIso : new Date(dateOrIso);
  if (Number.isNaN(d.getTime())) return null;

  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
}
