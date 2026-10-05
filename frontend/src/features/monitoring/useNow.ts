import * as React from "react";

/**
 * Hook providing a ticking timestamp updated on a fixed interval.
 * Allows pure time-dependent UI logic (such as stall detection) to refresh
 * without relying on incoming server data packets or query cache changes.
 */
export function useNow(intervalMs: number = 1000): number {
  const [now, setNow] = React.useState<number>(() => Date.now());

  React.useEffect(() => {
    const timerId = setInterval(() => {
      setNow(Date.now());
    }, intervalMs);

    return () => {
      clearInterval(timerId);
    };
  }, [intervalMs]);

  return now;
}
