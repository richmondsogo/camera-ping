import * as React from "react";
import { CameraTable } from "@/features/cameras/CameraTable";
import { CameraToolbar } from "@/features/cameras/CameraToolbar";
import { useCameras } from "@/features/cameras/queries";
import {
  filterCameras,
  getDistinctLocations,
  type StatusFilter,
} from "@/features/cameras/utils";
import type { CameraRead } from "@/lib/schemas";

export function DashboardPage() {
  const { data: cameras = [], isPending, isError, refetch } = useCameras();

  const [searchQuery, setSearchQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("all");
  const [locationFilter, setLocationFilter] = React.useState<string | null>(
    null
  );

  // Focus management refs
  const addCameraRef = React.useRef<HTMLButtonElement | null>(null);
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

  const handleEdit = React.useCallback((camera: CameraRead) => {
    // Will be wired to edit dialog in Checkpoint 6
    void camera;
  }, []);

  const handleDelete = React.useCallback((camera: CameraRead) => {
    // Will be wired to delete dialog in Checkpoint 6
    void camera;
  }, []);

  const handleAddCamera = React.useCallback(() => {
    // Will be wired to add dialog in Checkpoint 6
  }, []);

  return (
    <div className="flex flex-col gap-stack">
      <div className="flex items-center justify-between">
        <h1 className="text-page-title text-foreground">Dashboard</h1>
      </div>

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
      />

      <CameraTable
        cameras={filteredCameras}
        totalCameras={cameras.length}
        isPending={isPending}
        isError={isError}
        onRetry={() => void refetch()}
        onEdit={handleEdit}
        onDelete={handleDelete}
        editButtonRefs={editButtonRefs}
      />
    </div>
  );
}

export default DashboardPage;
