import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useDeleteCamera } from "@/features/cameras/queries";
import { mapServerErrors } from "@/features/cameras/utils";
import type { CameraRead } from "@/lib/schemas";

export interface DeleteCameraDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  camera: CameraRead | null;
  onSuccess?: (deletedCamera: CameraRead) => void;
}

export function DeleteCameraDialog({
  open,
  onOpenChange,
  camera,
  onSuccess,
}: DeleteCameraDialogProps) {
  const deleteCamera = useDeleteCamera();
  const isPending = deleteCamera.isPending;
  const [serverError, setServerError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (open) {
      setServerError(null);
    }
  }, [open]);

  const handleDelete = async () => {
    if (!camera || isPending) return;
    setServerError(null);

    try {
      await deleteCamera.mutateAsync(camera.id);
      onOpenChange(false);
      onSuccess?.(camera);
    } catch (err) {
      const mapped = mapServerErrors(err);
      setServerError(mapped.formError ?? "Failed to delete camera. Try again.");
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (isPending) return;
        onOpenChange(nextOpen);
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
        data-testid="delete-camera-dialog"
      >
        <DialogHeader>
          <DialogTitle data-testid="delete-dialog-title">
            Delete Camera
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete camera &ldquo;{camera?.camera_name}
            &rdquo; ({camera?.ip_address})? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        {serverError && (
          <div
            className="text-sm text-error"
            role="alert"
            data-testid="delete-dialog-error"
          >
            {serverError}
          </div>
        )}

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isPending}
            data-testid="cancel-delete-camera-button"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            disabled={isPending}
            data-testid="confirm-delete-camera-button"
          >
            {isPending ? "Deleting..." : "Delete Camera"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
