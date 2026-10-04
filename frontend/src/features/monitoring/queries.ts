import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CAMERAS_QUERY_KEY } from "@/features/cameras/queries";
import { api } from "@/lib/api";
import type { MonitoringStatus } from "@/lib/schemas";

export const MONITORING_STATUS_QUERY_KEY = ["monitoring", "status"] as const;
export const POLL_INTERVAL_MS = 5000;

/**
 * Hook to poll monitoring engine status every 5 seconds (configurable).
 */
export function useMonitoringStatus(
  pollInterval: number | false = POLL_INTERVAL_MS
) {
  return useQuery<MonitoringStatus>({
    queryKey: MONITORING_STATUS_QUERY_KEY,
    queryFn: () => api.getMonitoringStatus(),
    refetchInterval: pollInterval,
    refetchIntervalInBackground: true,
  });
}

/**
 * Mutation to start periodic monitoring.
 * Writes returned server status into query cache and invalidates status & camera queries.
 * Never retries on error.
 */
export function useStartMonitoring() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.startMonitoring(),
    retry: false,
    onSuccess: (data: MonitoringStatus) => {
      queryClient.setQueryData(MONITORING_STATUS_QUERY_KEY, data);
      return Promise.all([
        queryClient.invalidateQueries({
          queryKey: MONITORING_STATUS_QUERY_KEY,
        }),
        queryClient.invalidateQueries({ queryKey: CAMERAS_QUERY_KEY }),
      ]);
    },
  });
}

/**
 * Mutation to stop periodic monitoring.
 * Writes returned server status into query cache and invalidates status & camera queries.
 * Never retries on error.
 */
export function useStopMonitoring() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.stopMonitoring(),
    retry: false,
    onSuccess: (data: MonitoringStatus) => {
      queryClient.setQueryData(MONITORING_STATUS_QUERY_KEY, data);
      return Promise.all([
        queryClient.invalidateQueries({
          queryKey: MONITORING_STATUS_QUERY_KEY,
        }),
        queryClient.invalidateQueries({ queryKey: CAMERAS_QUERY_KEY }),
      ]);
    },
  });
}
