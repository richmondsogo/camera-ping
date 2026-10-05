import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Camera, CameraFormData } from "@/lib/schemas";

export const CAMERAS_QUERY_KEY = ["cameras"] as const;
export const DEFAULT_POLL_INTERVAL_MS = 5000;

/**
 * Query hook for camera list.
 * uses isPending for initial loading state; background refetches never blank the table.
 * Supports background polling every 5s by default; can be disabled or overridden in tests.
 */
export function useCameras(
  pollInterval: number | false = DEFAULT_POLL_INTERVAL_MS
) {
  return useQuery<Camera[]>({
    queryKey: CAMERAS_QUERY_KEY,
    queryFn: () => api.listCameras(),
    refetchInterval: pollInterval,
    refetchIntervalInBackground: true,
  });
}

/**
 * Mutation hook for creating a camera.
 * onSuccess returns invalidateQueries promise to ensure list is fresh before dialog closes.
 */
export function useCreateCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CameraFormData) => api.createCamera(data),
    onSuccess: () => {
      return queryClient.invalidateQueries({ queryKey: CAMERAS_QUERY_KEY });
    },
  });
}

/**
 * Mutation hook for updating a camera.
 * onSuccess returns invalidateQueries promise to ensure list is fresh before dialog closes.
 */
export function useUpdateCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CameraFormData> }) =>
      api.updateCamera(id, data),
    onSuccess: () => {
      return queryClient.invalidateQueries({ queryKey: CAMERAS_QUERY_KEY });
    },
  });
}

/**
 * Mutation hook for deleting a camera.
 * onSuccess returns invalidateQueries promise to ensure list is fresh before dialog closes.
 */
export function useDeleteCamera() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => api.deleteCamera(id),
    onSuccess: () => {
      return queryClient.invalidateQueries({ queryKey: CAMERAS_QUERY_KEY });
    },
  });
}
