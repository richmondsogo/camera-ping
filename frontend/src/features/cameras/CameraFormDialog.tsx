import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
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
import { Textarea } from "@/components/ui/textarea";
import { useCreateCamera, useUpdateCamera } from "@/features/cameras/queries";
import { mapServerErrors } from "@/features/cameras/utils";
import {
  type CameraFormData,
  type CameraRead,
  cameraFormSchema,
} from "@/lib/schemas";

export interface CameraFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  camera: CameraRead | null;
  onSuccess?: () => void;
}

export function CameraFormDialog({
  open,
  onOpenChange,
  camera,
  onSuccess,
}: CameraFormDialogProps) {
  const isEdit = Boolean(camera);
  const snapshotRef = React.useRef<CameraRead | null>(null);
  const [serverFormError, setServerFormError] = React.useState<string | null>(
    null
  );

  const createCamera = useCreateCamera();
  const updateCamera = useUpdateCamera();
  const isPending = createCamera.isPending || updateCamera.isPending;

  const {
    register,
    handleSubmit,
    reset,
    setError,
    watch,
    formState: { errors, dirtyFields },
  } = useForm<CameraFormData>({
    resolver: zodResolver(cameraFormSchema),
    defaultValues: {
      camera_name: "",
      location: "",
      description: "",
      ip_address: "",
    },
  });

  const latestCameraRef = React.useRef(camera);
  latestCameraRef.current = camera;

  // Snapshot on open: A background refetch while dialog is open must NEVER overwrite form
  React.useEffect(() => {
    if (open) {
      const initial = latestCameraRef.current;
      snapshotRef.current = initial;
      reset({
        camera_name: initial?.camera_name ?? "",
        location: initial?.location ?? "",
        description: initial?.description ?? "",
        ip_address: initial?.ip_address ?? "",
      });
      setServerFormError(null);
    }
  }, [open, reset]);

  // IP Warning: only if editing and IP changed from snapshot
  const watchedIp = watch("ip_address");
  const originalIp = snapshotRef.current?.ip_address;
  const showIpWarning =
    isEdit &&
    Boolean(originalIp) &&
    watchedIp.trim().length > 0 &&
    watchedIp.trim() !== originalIp?.trim();

  const onSubmit = async (data: CameraFormData) => {
    if (isPending) return;
    setServerFormError(null);

    try {
      if (isEdit && snapshotRef.current) {
        // Send only dirty fields on update
        const payload: Partial<CameraFormData> = {};
        if (dirtyFields.camera_name) payload.camera_name = data.camera_name;
        if (dirtyFields.location) payload.location = data.location;
        if (dirtyFields.description) payload.description = data.description;
        if (dirtyFields.ip_address) payload.ip_address = data.ip_address;

        if (Object.keys(payload).length > 0) {
          await updateCamera.mutateAsync({
            id: snapshotRef.current.id,
            data: payload,
          });
        }
      } else {
        await createCamera.mutateAsync(data);
      }

      onOpenChange(false);
      onSuccess?.();
    } catch (err) {
      const mapped = mapServerErrors(err);
      if (mapped.formError) {
        setServerFormError(mapped.formError);
      }
      for (const [field, message] of Object.entries(mapped.fieldErrors)) {
        setError(field as keyof CameraFormData, { message });
      }
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
        data-testid="camera-form-dialog"
      >
        <DialogHeader>
          <DialogTitle data-testid="dialog-title">
            {isEdit ? "Edit Camera" : "Add Camera"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Update camera settings and network configuration."
              : "Add a new network camera to monitor ICMP reachability."}
          </DialogDescription>
        </DialogHeader>

        {serverFormError && (
          <div
            className="text-sm text-error"
            role="alert"
            data-testid="dialog-form-error"
          >
            {serverFormError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-stack">
          {/* Camera Name */}
          <div className="space-y-tight">
            <Label htmlFor="camera_name">Camera Name</Label>
            <Input
              id="camera_name"
              placeholder="e.g. North Gate PTZ"
              disabled={isPending}
              aria-invalid={Boolean(errors.camera_name)}
              aria-describedby={
                errors.camera_name ? "camera_name-error" : undefined
              }
              {...register("camera_name")}
              data-testid="camera-name-input"
            />
            {errors.camera_name && (
              <p
                id="camera_name-error"
                className="text-xs text-error"
                data-testid="camera-name-error"
              >
                {errors.camera_name.message}
              </p>
            )}
          </div>

          {/* IP Address */}
          <div className="space-y-tight">
            <Label htmlFor="ip_address">IP Address</Label>
            <Input
              id="ip_address"
              placeholder="e.g. 192.168.1.64"
              disabled={isPending}
              aria-invalid={Boolean(errors.ip_address)}
              aria-describedby={
                errors.ip_address
                  ? "ip_address-error"
                  : showIpWarning
                    ? "ip_address-warning"
                    : undefined
              }
              {...register("ip_address")}
              data-testid="camera-ip-input"
            />
            {errors.ip_address && (
              <p
                id="ip_address-error"
                className="text-xs text-error"
                data-testid="camera-ip-error"
              >
                {errors.ip_address.message}
              </p>
            )}
            {showIpWarning && !errors.ip_address && (
              <p
                id="ip_address-warning"
                className="text-xs text-muted-foreground"
                data-testid="ip-change-warning"
              >
                Changing the IP address resets this camera's reachability
                statistics and monitoring history.
              </p>
            )}
          </div>

          {/* Location */}
          <div className="space-y-tight">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              placeholder="e.g. Warehouse B"
              disabled={isPending}
              aria-invalid={Boolean(errors.location)}
              aria-describedby={errors.location ? "location-error" : undefined}
              {...register("location")}
              data-testid="camera-location-input"
            />
            {errors.location && (
              <p
                id="location-error"
                className="text-xs text-error"
                data-testid="camera-location-error"
              >
                {errors.location.message}
              </p>
            )}
          </div>

          {/* Description */}
          <div className="space-y-tight">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Optional notes or details about camera placement..."
              disabled={isPending}
              aria-invalid={Boolean(errors.description)}
              aria-describedby={
                errors.description ? "description-error" : undefined
              }
              {...register("description")}
              data-testid="camera-description-input"
            />
            {errors.description && (
              <p
                id="description-error"
                className="text-xs text-error"
                data-testid="camera-description-error"
              >
                {errors.description.message}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
              data-testid="cancel-camera-form-button"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="default"
              disabled={isPending}
              data-testid="submit-camera-form-button"
            >
              {isPending
                ? isEdit
                  ? "Saving..."
                  : "Adding..."
                : isEdit
                  ? "Save Changes"
                  : "Add Camera"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
