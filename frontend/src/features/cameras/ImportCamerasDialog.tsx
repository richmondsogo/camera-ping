import * as React from "react";
import { Download, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError, type ApiErrorDetailItem } from "@/lib/api";
import type { CameraImportPreview, CameraImportSuccess } from "@/lib/schemas";

export interface ImportCamerasDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (count: number) => Promise<void> | void;
  importButtonRef?: React.RefObject<HTMLButtonElement | null>;
}

type ImportStatus = "idle" | "validating" | "valid" | "error" | "importing";

export function ImportCamerasDialog({
  open,
  onOpenChange,
  onSuccess,
  importButtonRef,
}: ImportCamerasDialogProps) {
  const [file, setFile] = React.useState<File | null>(null);
  const [status, setStatus] = React.useState<ImportStatus>("idle");
  const [preview, setPreview] = React.useState<CameraImportPreview | null>(
    null
  );
  const [errorItems, setErrorItems] = React.useState<ApiErrorDetailItem[]>([]);
  const [totalErrors, setTotalErrors] = React.useState<number>(0);
  const [serverAlertError, setServerAlertError] = React.useState<string | null>(
    null
  );
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const isPending = status === "validating" || status === "importing";

  // Reset dialog state when opened or closed
  React.useEffect(() => {
    if (open) {
      setFile(null);
      setStatus("idle");
      setPreview(null);
      setErrorItems([]);
      setTotalErrors(0);
      setServerAlertError(null);
    }
  }, [open]);

  const handleApiError = (err: unknown) => {
    const isNotReadable =
      (err instanceof Error &&
        (err.name === "NotReadableError" ||
          err.message.includes("NotReadableError"))) ||
      (typeof err === "object" &&
        err !== null &&
        "name" in err &&
        (err as { name: string }).name === "NotReadableError");

    if (isNotReadable) {
      setFile(null);
      setStatus("idle");
      setPreview(null);
      setErrorItems([]);
      setTotalErrors(0);
      setServerAlertError(
        "Couldn't read the file. Close it in Excel and choose it again."
      );
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    if (err instanceof ApiError) {
      if (err.kind === "network" || err.kind === "server") {
        setServerAlertError("Couldn't reach the server. Try again.");
        setStatus("idle");
        return;
      }

      if (err.status === 413) {
        setErrorItems([
          {
            loc: ["file"],
            msg: "File size exceeds 1 MiB limit.",
            type: "file_too_large",
          },
        ]);
        setTotalErrors(1);
        setStatus("error");
        return;
      }

      if (err.status === 409) {
        setServerAlertError(
          "Another camera with one of these IP addresses was added in the meantime. Nothing was imported. Try again."
        );
        setStatus("idle");
        return;
      }

      if (err.status === 422 && Array.isArray(err.detail)) {
        setErrorItems(err.detail);
        setTotalErrors(err.totalErrors ?? err.detail.length);
        setStatus("error");
        return;
      }

      setServerAlertError(err.message || "Request failed.");
      setStatus("idle");
      return;
    }

    setServerAlertError("An unexpected error occurred.");
    setStatus("idle");
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setServerAlertError(null);
    setStatus("validating");

    try {
      const res = await api.importCameras(selectedFile, true);
      setPreview(res as CameraImportPreview);
      setStatus("valid");
    } catch (err: unknown) {
      handleApiError(err);
    }
  };

  const handleConfirmImport = async () => {
    if (!file) return;
    setStatus("importing");
    setServerAlertError(null);

    try {
      const res = await api.importCameras(file, false);
      const count = (res as CameraImportSuccess).imported;
      await onSuccess(count);
      onOpenChange(false);
      requestAnimationFrame(() => {
        importButtonRef?.current?.focus();
      });
    } catch (err: unknown) {
      handleApiError(err);
    }
  };

  const handleResetFileChoice = () => {
    setFile(null);
    setStatus("idle");
    setPreview(null);
    setErrorItems([]);
    setTotalErrors(0);
    setServerAlertError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const count = preview?.count ?? 0;
  const countText =
    count === 1 ? "1 camera will be added." : `${count} cameras will be added.`;
  const confirmBtnText =
    count === 1 ? "Import 1 camera" : `Import ${count} cameras`;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!isPending) {
          onOpenChange(next);
          if (!next) {
            importButtonRef?.current?.focus();
          }
        }
      }}
    >
      <DialogContent
        showCloseButton={!isPending}
        onKeyDown={(e: React.KeyboardEvent) => {
          if (isPending && e.key === "Escape") {
            e.preventDefault();
            e.stopPropagation();
          }
        }}
        onPointerDown={(e: React.PointerEvent) => {
          if (isPending) {
            e.preventDefault();
          }
        }}
        className="w-dialog-wide"
        data-testid="import-cameras-dialog"
      >
        <DialogHeader>
          <DialogTitle>Import Cameras</DialogTitle>
          <DialogDescription>
            Upload a CSV file to import multiple cameras into your inventory.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-stack">
          {/* Server Error Alert */}
          {serverAlertError && (
            <div
              role="alert"
              className="rounded-control border border-destructive/50 bg-destructive/10 p-control-x text-sm text-destructive"
              data-testid="import-server-alert"
            >
              {serverAlertError}
            </div>
          )}

          {/* Template Guidance & Instructions */}
          <div className="rounded-control border border-border bg-muted/30 p-control-x text-xs">
            <div className="flex items-center justify-between pb-tight">
              <span className="font-semibold text-foreground">
                Required CSV Format:
              </span>
              <a
                href="/api/cameras/import/template"
                download
                className="inline-flex items-center gap-1 text-primary hover:underline"
                data-testid="download-template-link"
              >
                <Download className="size-3" />
                <span>Download template</span>
              </a>
            </div>
            <div className="font-mono text-muted-foreground">
              camera_name,location,description,ip_address
            </div>
            <div className="pt-1 text-muted-foreground">
              Example: Server Room Rack A,Server Room,Rack A switch,192.0.2.101
            </div>
          </div>

          {/* File input state */}
          {status === "idle" && (
            <div className="flex flex-col gap-tight">
              <Label htmlFor="camera-csv-file" className="text-sm font-medium">
                Choose CSV file
              </Label>
              <Input
                ref={fileInputRef}
                id="camera-csv-file"
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                disabled={isPending}
                data-testid="csv-file-input"
              />
            </div>
          )}

          {/* Validating state */}
          {status === "validating" && (
            <div
              className="flex items-center gap-inline py-stack text-sm text-muted-foreground"
              data-testid="import-validating-indicator"
            >
              <span>Validating file...</span>
            </div>
          )}

          {/* Error State */}
          {status === "error" && (
            <div
              className="flex flex-col gap-tight"
              data-testid="import-error-view"
            >
              <p className="text-sm font-semibold text-destructive">
                {totalErrors === 1
                  ? "1 problem found. Nothing was imported."
                  : `${totalErrors} problems found. Nothing was imported.`}
              </p>

              <div className="max-h-60 overflow-y-auto rounded-control border border-border">
                <table className="w-full text-left text-table">
                  <thead className="sticky top-0 bg-muted text-xs font-medium text-muted-foreground">
                    <tr>
                      <th className="px-button-x py-tight w-16">Line</th>
                      <th className="px-button-x py-tight w-28">Column</th>
                      <th className="px-button-x py-tight">Problem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {errorItems.map((item, idx) => {
                      const line =
                        item.loc.length >= 2 && typeof item.loc[1] === "number"
                          ? item.loc[1]
                          : "-";
                      const column =
                        item.loc.length >= 3
                          ? String(item.loc[2])
                          : item.loc.length === 1 && item.loc[0] === "file"
                            ? "file"
                            : "-";

                      return (
                        <tr key={idx} className="hover:bg-muted/40">
                          <td className="px-button-x py-tight text-muted-foreground">
                            {line}
                          </td>
                          <td className="px-button-x py-tight font-mono text-xs">
                            {column}
                          </td>
                          <td className="px-button-x py-tight text-foreground">
                            {item.msg}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {totalErrors > errorItems.length && (
                <p className="text-xs text-muted-foreground">
                  Showing the first {errorItems.length} of {totalErrors}{" "}
                  problems.
                </p>
              )}

              <div className="pt-tight">
                <Button
                  type="button"
                  variant="outline"
                  size="default"
                  onClick={handleResetFileChoice}
                  data-testid="choose-another-file-button"
                >
                  Choose another file
                </Button>
              </div>
            </div>
          )}

          {/* Valid Preview State */}
          {(status === "valid" || status === "importing") && preview && (
            <div
              className="flex flex-col gap-tight"
              data-testid="import-preview-view"
            >
              <p className="text-sm font-semibold text-foreground">
                {countText}
              </p>

              <div className="max-h-60 overflow-y-auto rounded-control border border-border">
                <table className="w-full text-left text-table">
                  <thead className="sticky top-0 bg-muted text-xs font-medium text-muted-foreground">
                    <tr>
                      <th className="px-button-x py-tight">Name</th>
                      <th className="px-button-x py-tight">Location</th>
                      <th className="px-button-x py-tight">Description</th>
                      <th className="px-button-x py-tight">IP Address</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {preview.preview.map((row, idx) => (
                      <tr key={idx} className="hover:bg-muted/40">
                        <td className="px-button-x py-tight font-medium">
                          {row.camera_name}
                        </td>
                        <td className="px-button-x py-tight text-muted-foreground">
                          {row.location}
                        </td>
                        <td className="px-button-x py-tight text-muted-foreground truncate max-w-xs">
                          {row.description}
                        </td>
                        <td className="px-button-x py-tight font-mono">
                          {row.ip_address}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            disabled={isPending}
            onClick={() => {
              onOpenChange(false);
              importButtonRef?.current?.focus();
            }}
            data-testid="import-cancel-button"
          >
            Cancel
          </Button>

          {(status === "valid" || status === "importing") && (
            <Button
              type="button"
              variant="default"
              disabled={isPending}
              onClick={handleConfirmImport}
              data-testid="import-confirm-button"
            >
              <Upload className="size-4" />
              <span>{isPending ? "Importing..." : confirmBtnText}</span>
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
