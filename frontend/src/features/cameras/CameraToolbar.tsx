import { Download, Plus, Search, Upload } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ALL_LOCATIONS_VALUE,
  type StatusFilter,
} from "@/features/cameras/utils";
import { cn } from "@/lib/utils";

export interface CameraToolbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  statusFilter: StatusFilter;
  onStatusChange: (status: StatusFilter) => void;
  locationFilter: string | null;
  onLocationChange: (location: string | null) => void;
  distinctLocations: string[];
  totalCameras: number;
  filteredCameras: number;
  onAddCamera: () => void;
  addCameraRef?: React.RefObject<HTMLButtonElement | null>;
  onImportCameras?: () => void;
  importRef?: React.RefObject<HTMLButtonElement | null>;
  isExportDisabled?: boolean;
}

export function CameraToolbar({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusChange,
  locationFilter,
  onLocationChange,
  distinctLocations,
  totalCameras,
  filteredCameras,
  onAddCamera,
  addCameraRef,
  onImportCameras,
  importRef,
  isExportDisabled = false,
}: CameraToolbarProps) {
  const isControlsDisabled = totalCameras === 0;
  const cameraNoun = totalCameras === 1 ? "camera" : "cameras";
  const countLine = `Showing ${filteredCameras} of ${totalCameras} ${cameraNoun}`;

  return (
    <div
      data-slot="camera-toolbar"
      className="flex flex-col gap-toolbar sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex flex-1 flex-wrap items-center gap-inline">
        {/* Search Input */}
        <div className="relative min-w-48 max-w-xs flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search cameras..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            disabled={isControlsDisabled}
            className="pl-9"
            aria-label="Search cameras"
            data-testid="camera-search-input"
          />
        </div>

        {/* Status Filter */}
        <div className="w-36">
          <Select
            value={statusFilter}
            onValueChange={(val) => onStatusChange(val as StatusFilter)}
            disabled={isControlsDisabled}
          >
            <SelectTrigger
              aria-label="Filter by status"
              data-testid="status-filter-trigger"
            >
              <SelectValue placeholder="All Statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="online">Online</SelectItem>
              <SelectItem value="offline">Offline</SelectItem>
              <SelectItem value="unknown">Unknown</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Location Filter */}
        <div className="w-40">
          <Select
            value={
              locationFilter === null ? ALL_LOCATIONS_VALUE : locationFilter
            }
            onValueChange={(val) =>
              onLocationChange(val === ALL_LOCATIONS_VALUE ? null : val)
            }
            disabled={isControlsDisabled}
          >
            <SelectTrigger
              aria-label="Filter by location"
              data-testid="location-filter-trigger"
            >
              <SelectValue placeholder="All Locations" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_LOCATIONS_VALUE}>All Locations</SelectItem>
              {distinctLocations.map((loc) => (
                <SelectItem key={loc} value={loc}>
                  {loc}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center justify-between gap-inline sm:justify-end">
        {/* Count Line */}
        <span
          className="text-sm text-muted-foreground whitespace-nowrap"
          data-testid="camera-count-line"
        >
          {countLine}
        </span>

        {/* Import Button */}
        <Button
          ref={importRef}
          onClick={onImportCameras}
          variant="outline"
          size="default"
          data-testid="import-cameras-toolbar-button"
        >
          <Upload className="size-4" />
          <span>Import</span>
        </Button>

        {/* Export Button / Link */}
        {isExportDisabled ? (
          <Button
            variant="outline"
            size="default"
            disabled
            data-testid="export-cameras-toolbar-button"
          >
            <Download className="size-4" />
            <span>Export</span>
          </Button>
        ) : (
          <a
            href="/api/cameras/export"
            download
            className={cn(
              buttonVariants({ variant: "outline", size: "default" })
            )}
            data-testid="export-cameras-toolbar-button"
          >
            <Download className="size-4" />
            <span>Export</span>
          </a>
        )}

        {/* Add Camera Button */}
        <Button
          ref={addCameraRef}
          onClick={onAddCamera}
          variant="default"
          size="default"
          data-testid="add-camera-toolbar-button"
        >
          <Plus className="size-4" />
          <span>Add Camera</span>
        </Button>
      </div>
    </div>
  );
}
