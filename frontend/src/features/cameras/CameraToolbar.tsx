import * as React from "react";
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

const STATUS_SELECT_ITEMS: ReadonlyArray<{
  value: StatusFilter;
  label: string;
}> = [
  { value: "all", label: "All Statuses" },
  { value: "online", label: "Online" },
  { value: "offline", label: "Offline" },
  { value: "unknown", label: "Unknown" },
];

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
  onClearFilters?: () => void;
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
  onClearFilters,
}: CameraToolbarProps) {
  const isControlsDisabled = totalCameras === 0;
  const cameraNoun = totalCameras === 1 ? "camera" : "cameras";
  const countLine = `Showing ${filteredCameras} of ${totalCameras} ${cameraNoun}`;

  const searchInputRef = React.useRef<HTMLInputElement | null>(null);

  const hasActiveFilters =
    searchQuery.trim().length > 0 ||
    statusFilter !== "all" ||
    locationFilter !== null;

  const handleClearFilters = React.useCallback(() => {
    onSearchChange("");
    onStatusChange("all");
    onLocationChange(null);
    onClearFilters?.();
    searchInputRef.current?.focus();
  }, [onSearchChange, onStatusChange, onLocationChange, onClearFilters]);

  const locationSelectItems = React.useMemo(
    () => [
      { value: ALL_LOCATIONS_VALUE, label: "All Locations" },
      ...distinctLocations.map((loc) => ({ value: loc, label: loc })),
    ],
    [distinctLocations]
  );

  return (
    <div className="flex flex-col gap-tight">
      <div
        data-slot="camera-toolbar"
        className="flex flex-wrap items-center justify-between gap-inline"
      >
        <div className="flex flex-wrap items-center gap-inline">
          {/* Search Input */}
          <div className="relative min-w-48 max-w-xs flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              ref={searchInputRef}
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
          <Select
            items={STATUS_SELECT_ITEMS}
            value={statusFilter}
            onValueChange={(val) => onStatusChange(val as StatusFilter)}
            disabled={isControlsDisabled}
          >
            <SelectTrigger
              className="w-trigger-status"
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

          {/* Location Filter */}
          <Select
            items={locationSelectItems}
            value={
              locationFilter === null ? ALL_LOCATIONS_VALUE : locationFilter
            }
            onValueChange={(val) =>
              onLocationChange(val === ALL_LOCATIONS_VALUE ? null : val)
            }
            disabled={isControlsDisabled}
          >
            <SelectTrigger
              className="w-trigger-location"
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

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="default"
              onClick={handleClearFilters}
              data-testid="clear-filters-toolbar-button"
            >
              Clear filters
            </Button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-tight">
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

      {/* Count Line */}
      <p
        aria-live="polite"
        className="text-sm text-muted-foreground"
        data-testid="camera-count-line"
      >
        {countLine}
      </p>
    </div>
  );
}
