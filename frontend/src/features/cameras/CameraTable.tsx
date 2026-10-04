import * as React from "react";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatLastChecked } from "@/features/cameras/utils";
import { formatCheckCount } from "@/features/monitoring/utils";
import type { CameraRead } from "@/lib/schemas";

export interface CameraTableProps {
  cameras: CameraRead[];
  totalCameras: number;
  isPending: boolean;
  isError: boolean;
  onRetry: () => void;
  onEdit: (camera: CameraRead) => void;
  onDelete: (camera: CameraRead) => void;
  editButtonRefs?: React.MutableRefObject<Map<number, HTMLButtonElement>>;
  onClearFilters?: () => void;
}

export function CameraTable({
  cameras,
  totalCameras,
  isPending,
  isError,
  onRetry,
  onEdit,
  onDelete,
  editButtonRefs,
  onClearFilters,
}: CameraTableProps) {
  const columns = React.useMemo<ColumnDef<CameraRead>[]>(
    () => [
      {
        id: "status",
        header: () => "Status",
        cell: ({ row }) => {
          const status = row.original.status;
          const statusColor =
            status === "online"
              ? "bg-status-online"
              : status === "offline"
                ? "bg-status-offline"
                : "bg-status-unknown";
          const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
          const failures = row.original.consecutive_failures;
          const checkCountText =
            status === "offline" && failures > 0
              ? formatCheckCount(failures)
              : null;

          return (
            <div className="flex items-center gap-tight whitespace-nowrap">
              <span
                data-slot="status-dot"
                className={`size-2 shrink-0 rounded-full ${statusColor}`}
                aria-hidden="true"
              />
              <span data-slot="status-label">{statusLabel}</span>
              {checkCountText && (
                <span
                  data-slot="status-failures"
                  className="text-xs text-muted-foreground"
                  title={`Failed ${failures} consecutive checks`}
                >
                  {checkCountText}
                </span>
              )}
            </div>
          );
        },
      },
      {
        id: "camera_name",
        header: () => "Camera Name",
        cell: ({ row }) => {
          const name = row.original.camera_name;
          return (
            <div className="truncate font-medium" title={name}>
              {name}
            </div>
          );
        },
      },
      {
        id: "ip_address",
        header: () => "IP Address",
        cell: ({ row }) => {
          const ip = row.original.ip_address;
          return (
            <div className="tabular-nums whitespace-nowrap" title={ip}>
              {ip}
            </div>
          );
        },
      },
      {
        id: "location",
        header: () => "Location",
        cell: ({ row }) => {
          const loc = row.original.location;
          return (
            <div
              className="truncate text-muted-foreground"
              title={loc ?? undefined}
            >
              {loc && loc.trim().length > 0 ? loc : "—"}
            </div>
          );
        },
      },
      {
        id: "description",
        header: () => "Description",
        cell: ({ row }) => {
          const desc = row.original.description;
          return (
            <div
              data-testid="table-cell-description"
              className="truncate text-muted-foreground"
              title={desc ?? undefined}
            >
              {desc && desc.trim().length > 0 ? desc : "—"}
            </div>
          );
        },
      },
      {
        id: "last_checked",
        header: () => "Last Checked",
        cell: ({ row }) => {
          const formatted = formatLastChecked(row.original.last_checked);
          return (
            <div
              className="tabular-nums whitespace-nowrap text-muted-foreground"
              title={formatted.title}
            >
              {formatted.text}
            </div>
          );
        },
      },
      {
        id: "actions",
        header: () => <span className="sr-only">Actions</span>,
        cell: ({ row }) => {
          const camera = row.original;
          return (
            <div className="flex items-center justify-end gap-tight whitespace-nowrap">
              <Button
                ref={(el) => {
                  if (editButtonRefs) {
                    if (el) {
                      editButtonRefs.current.set(camera.id, el);
                    } else {
                      editButtonRefs.current.delete(camera.id);
                    }
                  }
                }}
                variant="ghost"
                size="sm"
                onClick={() => onEdit(camera)}
                data-testid={`edit-camera-${camera.id}`}
                aria-label={`Edit ${camera.camera_name}`}
              >
                Edit
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete(camera)}
                className="text-destructive hover:text-destructive"
                data-testid={`delete-camera-${camera.id}`}
                aria-label={`Delete ${camera.camera_name}`}
              >
                Delete
              </Button>
            </div>
          );
        },
      },
    ],
    [onEdit, onDelete, editButtonRefs]
  );

  // useReactTable hook handles the table instance
  const table = useReactTable({
    data: cameras,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Table className="min-w-table-min table-fixed w-full">
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => {
              let widthClass = "";
              if (header.id === "status") widthClass = "w-col-status";
              else if (header.id === "ip_address") widthClass = "w-col-ip";
              else if (header.id === "description") widthClass = "w-3/12";
              else if (header.id === "last_checked")
                widthClass = "w-col-checked";
              else if (header.id === "actions")
                widthClass = "w-col-actions text-right";

              return (
                <TableHead key={header.id} className={widthClass}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                </TableHead>
              );
            })}
          </TableRow>
        ))}
      </TableHeader>

      <TableBody>
        {/* 1. First-time Loading Skeleton */}
        {isPending ? (
          Array.from({ length: 4 }).map((_, idx) => (
            <TableRow
              key={`skeleton-${idx}`}
              data-testid="loading-cameras-skeleton"
            >
              <TableCell className="w-col-status">
                <div className="h-4 w-16 animate-pulse rounded bg-muted" />
              </TableCell>
              <TableCell>
                <div className="h-4 w-28 animate-pulse rounded bg-muted" />
              </TableCell>
              <TableCell className="w-col-ip">
                <div className="h-4 w-24 animate-pulse rounded bg-muted" />
              </TableCell>
              <TableCell>
                <div className="h-4 w-20 animate-pulse rounded bg-muted" />
              </TableCell>
              <TableCell className="w-3/12">
                <div className="h-4 w-40 animate-pulse rounded bg-muted" />
              </TableCell>
              <TableCell className="w-col-checked">
                <div className="h-4 w-32 animate-pulse rounded bg-muted" />
              </TableCell>
              <TableCell className="w-col-actions text-right">
                <div className="ml-auto h-7 w-20 animate-pulse rounded bg-muted" />
              </TableCell>
            </TableRow>
          ))
        ) : isError && cameras.length === 0 ? (
          /* 2. Error State with Retry */
          <TableRow>
            <TableCell
              colSpan={7}
              className="h-48 text-center"
              data-testid="error-cameras-state"
            >
              <div className="flex flex-col items-center justify-center gap-tight">
                <p className="text-sm text-muted-foreground">
                  Failed to load cameras.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRetry}
                  data-testid="retry-cameras-button"
                >
                  Retry
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ) : cameras.length === 0 ? (
          /* 3. Empty States */
          <TableRow>
            <TableCell
              colSpan={7}
              className="h-48 text-center text-sm text-muted-foreground"
              data-testid={
                totalCameras === 0
                  ? "empty-cameras-state"
                  : "filtered-empty-cameras-state"
              }
            >
              {totalCameras === 0 ? (
                "No cameras yet. Add your first camera to start monitoring."
              ) : (
                <div className="flex flex-col items-center justify-center gap-tight">
                  <p>No cameras match the current filters.</p>
                  {onClearFilters && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={onClearFilters}
                      data-testid="table-clear-filters-button"
                    >
                      Clear filters
                    </Button>
                  )}
                </div>
              )}
            </TableCell>
          </TableRow>
        ) : (
          /* 4. Data Rows */
          table.getRowModel().rows.map((row) => (
            <TableRow
              key={row.id}
              data-testid={`camera-row-${row.original.id}`}
            >
              {row.getVisibleCells().map((cell) => {
                let widthClass = "";
                if (cell.column.id === "status") widthClass = "w-col-status";
                else if (cell.column.id === "ip_address")
                  widthClass = "w-col-ip";
                else if (cell.column.id === "description")
                  widthClass = "w-3/12";
                else if (cell.column.id === "last_checked")
                  widthClass = "w-col-checked";
                else if (cell.column.id === "actions")
                  widthClass = "w-col-actions";

                return (
                  <TableCell key={cell.id} className={widthClass}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                );
              })}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
