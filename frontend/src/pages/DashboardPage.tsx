import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { CameraFormDialog } from "@/features/cameras/CameraFormDialog";
import { CameraTable } from "@/features/cameras/CameraTable";
import { CameraToolbar } from "@/features/cameras/CameraToolbar";
import { DeleteCameraDialog } from "@/features/cameras/DeleteCameraDialog";
import { ImportCamerasDialog } from "@/features/cameras/ImportCamerasDialog";
import { CAMERAS_QUERY_KEY, useCameras } from "@/features/cameras/queries";
import {
  filterCameras,
  getDistinctLocations,
  type StatusFilter,
} from "@/features/cameras/utils";
import { MonitoringPanel } from "@/features/monitoring/MonitoringPanel";
import {
  useMonitoringStatus,
  useStartMonitoring,
  useStopMonitoring,
} from "@/features/monitoring/queries";
import { countByStatus } from "@/features/monitoring/utils";
import type { CameraRead } from "@/lib/schemas";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const {
    data: cameras = [],
    isPending,
    isError: isCamerasError,
    dataUpdatedAt: camerasUpdatedAt,
    refetch,
  } = useCameras();

  const {
    data: monitoringStatus,
    isError: isStatusError,
    dataUpdatedAt: statusUpdatedAt,
  } = useMonitoringStatus();

  const startMutation = useStartMonitoring();
  const stopMutation = useStopMonitoring();

  const initialMountTime = React.useRef(Date.now()).current;
  const lastSuccessTime = React.useMemo(() => {
    const maxUpdated = Math.max(camerasUpdatedAt, statusUpdatedAt);
    return maxUpdated > 0 ? maxUpdated : initialMountTime;
  }, [camerasUpdatedAt, statusUpdatedAt, initialMountTime]);

  const isConnectionLost = isCamerasError || isStatusError;
  const counts = React.useMemo(() => countByStatus(cameras), [cameras]);

  // Tab title: (N offline) Camera Monitor when offline > 0, else Camera Monitor. Restore on unmount.
  React.useEffect(() => {
    if (counts.offline > 0) {
      document.title = `(${counts.offline} offline) Camera Monitor`;
    } else {
      document.title = "Camera Monitor";
    }
    return () => {
      document.title = "Camera Monitor";
    };
  }, [counts.offline]);

  const handleStart = React.useCallback(async () => {
    await startMutation.mutateAsync();
  }, [startMutation]);

  const handleStop = React.useCallback(async () => {
    await stopMutation.mutateAsync();
  }, [stopMutation]);

  const [searchQuery, setSearchQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("all");
  const [locationFilter, setLocationFilter] = React.useState<string | null>(
    null
  );

  // Dialog state
  const [formDialogOpen, setFormDialogOpen] = React.useState(false);
  const [formDialogCamera, setFormDialogCamera] =
    React.useState<CameraRead | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);
  const [deleteDialogCamera, setDeleteDialogCamera] =
    React.useState<CameraRead | null>(null);
  const [importDialogOpen, setImportDialogOpen] = React.useState(false);

  // Screen reader status announcement
  const [announcement, setAnnouncement] = React.useState("");

  // Focus management refs
  const addCameraRef = React.useRef<HTMLButtonElement | null>(null);
  const importButtonRef = React.useRef<HTMLButtonElement | null>(null);
  const editButtonRefs = React.useRef<Map<number, HTMLButtonElement>>(
    new Map()
  );

  // Filtered cameras and locations
  const filteredCameras = React.useMemo(
    () => filterCameras(cameras, searchQuery, statusFilter, locationFilter),
    [cameras, searchQuery, statusFilter, locationFilter]
  );

  const distinctLocations = React.useMemo(
    () => getDistinctLocations(cameras),
    [cameras]
  );

  // Focus return helper
  const restoreFocus = React.useCallback(
    (target: HTMLElement | null | undefined) => {
      // Wait for dialog unmount / DOM tick
      requestAnimationFrame(() => {
        if (target && document.contains(target)) {
          target.focus();
        } else if (addCameraRef.current) {
          addCameraRef.current.focus();
        }
      });
    },
    []
  );

  const handleAddCamera = React.useCallback(() => {
    setFormDialogCamera(null);
    setFormDialogOpen(true);
  }, []);

  const handleEdit = React.useCallback((camera: CameraRead) => {
    setFormDialogCamera(camera);
    setFormDialogOpen(true);
  }, []);

  const handleDelete = React.useCallback((camera: CameraRead) => {
    setDeleteDialogCamera(camera);
    setDeleteDialogOpen(true);
  }, []);

  const handleFormDialogClose = React.useCallback(
    (open: boolean) => {
      setFormDialogOpen(open);
      if (!open) {
        // Return focus: after add -> Add Camera button; after edit or cancel -> that row's Edit button
        if (formDialogCamera) {
          const btn = editButtonRefs.current.get(formDialogCamera.id);
          restoreFocus(btn ?? addCameraRef.current);
        } else {
          restoreFocus(addCameraRef.current);
        }
      }
    },
    [formDialogCamera, restoreFocus]
  );

  const handleDeleteDialogClose = React.useCallback(
    (open: boolean) => {
      setDeleteDialogOpen(open);
      if (!open && deleteDialogCamera) {
        // If cancelled without deleting, restore focus to that camera's Edit button
        const btn = editButtonRefs.current.get(deleteDialogCamera.id);
        restoreFocus(btn ?? addCameraRef.current);
      }
    },
    [deleteDialogCamera, restoreFocus]
  );

  const handleDeleteSuccess = React.useCallback(
    (deletedCamera: CameraRead) => {
      setAnnouncement(`Camera "${deletedCamera.camera_name}" deleted.`);

      // Target after delete: next row's Edit button, else previous row's Edit button, else Add Camera button
      const deletedIndex = filteredCameras.findIndex(
        (c) => c.id === deletedCamera.id
      );
      const nextCamera =
        deletedIndex !== -1 && deletedIndex + 1 < filteredCameras.length
          ? filteredCameras[deletedIndex + 1]
          : null;
      const prevCamera =
        deletedIndex > 0 ? filteredCameras[deletedIndex - 1] : null;

      requestAnimationFrame(() => {
        if (nextCamera && editButtonRefs.current.has(nextCamera.id)) {
          editButtonRefs.current.get(nextCamera.id)?.focus();
        } else if (prevCamera && editButtonRefs.current.has(prevCamera.id)) {
          editButtonRefs.current.get(prevCamera.id)?.focus();
        } else if (addCameraRef.current) {
          addCameraRef.current.focus();
        }
      });
    },
    [filteredCameras]
  );

  const handleFormSuccess = React.useCallback(() => {
    if (formDialogCamera) {
      setAnnouncement(`Camera "${formDialogCamera.camera_name}" updated.`);
    } else {
      setAnnouncement("Camera added successfully.");
    }
  }, [formDialogCamera]);

  const handleImportSuccess = React.useCallback(
    async (count: number) => {
      await queryClient.invalidateQueries({ queryKey: CAMERAS_QUERY_KEY });
      const message =
        count === 1 ? "1 camera imported." : `${count} cameras imported.`;
      setAnnouncement(message);
      restoreFocus(importButtonRef.current);
    },
    [queryClient, restoreFocus]
  );

  const handleClearFilters = React.useCallback(() => {
    setSearchQuery("");
    setStatusFilter("all");
    setLocationFilter(null);
  }, []);

  const isExportDisabled = isPending || isCamerasError || cameras.length === 0;

  return (
    <div className="flex flex-col gap-stack">
      {/* Screen Reader Live Region */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="polite-announcer"
      >
        {announcement}
      </div>

      <div className="flex items-center justify-between">
        <h1 className="text-page-title text-foreground">Dashboard</h1>
      </div>

      <MonitoringPanel
        status={monitoringStatus}
        counts={counts}
        isStarting={startMutation.isPending}
        isStopping={stopMutation.isPending}
        onStart={handleStart}
        onStop={handleStop}
        startError={startMutation.isError}
        stopError={stopMutation.isError}
        isConnectionLost={isConnectionLost}
        lastSuccessTime={lastSuccessTime}
      />

      <CameraToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        locationFilter={locationFilter}
        onLocationChange={setLocationFilter}
        distinctLocations={distinctLocations}
        totalCameras={cameras.length}
        filteredCameras={filteredCameras.length}
        onAddCamera={handleAddCamera}
        addCameraRef={addCameraRef}
        onImportCameras={() => setImportDialogOpen(true)}
        importRef={importButtonRef}
        isExportDisabled={isExportDisabled}
        onClearFilters={handleClearFilters}
      />

      <CameraTable
        cameras={filteredCameras}
        totalCameras={cameras.length}
        isPending={isPending}
        isError={isCamerasError}
        onRetry={() => void refetch()}
        onEdit={handleEdit}
        onDelete={handleDelete}
        editButtonRefs={editButtonRefs}
        onClearFilters={handleClearFilters}
      />

      {/* Add / Edit Dialog */}
      <CameraFormDialog
        open={formDialogOpen}
        onOpenChange={handleFormDialogClose}
        camera={formDialogCamera}
        onSuccess={handleFormSuccess}
      />

      {/* Delete Confirmation Dialog */}
      <DeleteCameraDialog
        open={deleteDialogOpen}
        onOpenChange={handleDeleteDialogClose}
        camera={deleteDialogCamera}
        onSuccess={handleDeleteSuccess}
      />

      {/* Import Cameras Dialog */}
      <ImportCamerasDialog
        open={importDialogOpen}
        onOpenChange={setImportDialogOpen}
        onSuccess={handleImportSuccess}
        importButtonRef={importButtonRef}
      />
    </div>
  );
}

export default DashboardPage;
