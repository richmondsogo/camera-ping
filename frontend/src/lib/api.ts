import { z } from "zod";
import {
  apiErrorResponseSchema,
  cameraImportPreviewSchema,
  cameraImportSuccessSchema,
  cameraListSchema,
  cameraReadSchema,
  type ApiErrorDetailItem,
  type Camera,
  type CameraFormData,
  type CameraImportPreview,
  type CameraImportSuccess,
} from "./schemas";

export type ApiErrorKind = "network" | "server" | "http" | "invalid-response";

export type { ApiErrorDetailItem };

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  readonly detail: string | ApiErrorDetailItem[] | null;
  readonly totalErrors?: number;

  constructor({
    kind,
    status,
    message,
    detail = null,
    totalErrors,
  }: {
    kind: ApiErrorKind;
    status: number;
    message: string;
    detail?: string | ApiErrorDetailItem[] | null;
    totalErrors?: number;
  }) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.totalErrors = totalErrors;
  }
}

export async function apiRequest<T>(
  url: string,
  options?: RequestInit,
  schema?: z.ZodType<T>
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, options);
  } catch (err) {
    if (
      (err instanceof Error &&
        (err.name === "NotReadableError" ||
          err.message.includes("NotReadableError"))) ||
      (typeof err === "object" &&
        err !== null &&
        "name" in err &&
        (err as { name: string }).name === "NotReadableError")
    ) {
      throw err;
    }
    throw new ApiError({
      kind: "network",
      status: 0,
      message: "Couldn't reach the server. Try again.",
    });
  }

  // 204 No Content: no body to parse
  if (res.status === 204) {
    return undefined as unknown as T;
  }

  // Any 5xx becomes ApiError kind "server"
  if (res.status >= 500) {
    throw new ApiError({
      kind: "server",
      status: res.status,
      message: "Couldn't reach the server. Try again.",
    });
  }

  const rawText = await res.text();
  let parsedJson: unknown = null;
  let hasValidJson = false;

  if (rawText.trim().length > 0) {
    try {
      parsedJson = JSON.parse(rawText);
      hasValidJson = true;
    } catch {
      hasValidJson = false;
    }
  }

  // If status is not 2xx
  if (!res.ok) {
    // Non-JSON or empty error body from proxy or server becomes "server"
    if (!hasValidJson) {
      throw new ApiError({
        kind: "server",
        status: res.status,
        message: "Couldn't reach the server. Try again.",
      });
    }

    let detail: string | ApiErrorDetailItem[] | null = null;
    let message = "Request failed.";
    let totalErrors: number | undefined;

    const errorParse = apiErrorResponseSchema.safeParse(parsedJson);
    if (errorParse.success) {
      const d = errorParse.data.detail;
      totalErrors = errorParse.data.total_errors;
      if (typeof d === "string") {
        detail = d;
        message = d;
      } else if (Array.isArray(d)) {
        detail = d;
        message = d.map((item) => item.msg).join("; ");
      }
    } else if (
      parsedJson &&
      typeof parsedJson === "object" &&
      "detail" in parsedJson
    ) {
      const d = (parsedJson as { detail: unknown }).detail;
      if (typeof d === "string") {
        detail = d;
        message = d;
      } else if (Array.isArray(d)) {
        detail = d as ApiErrorDetailItem[];
        message = (d as { msg?: string }[])
          .map((item) => item.msg ?? "Invalid value")
          .join("; ");
      }
      if (
        "total_errors" in parsedJson &&
        typeof (parsedJson as { total_errors?: unknown }).total_errors ===
          "number"
      ) {
        totalErrors = (parsedJson as { total_errors: number }).total_errors;
      }
    }

    throw new ApiError({
      kind: "http",
      status: res.status,
      message,
      detail,
      totalErrors,
    });
  }

  // If success, validate response body with schema if provided
  if (schema) {
    const parseResult = schema.safeParse(parsedJson);
    if (!parseResult.success) {
      throw new ApiError({
        kind: "invalid-response",
        status: res.status,
        message: "Invalid response received from server.",
        detail: parseResult.error.message,
      });
    }
    return parseResult.data;
  }

  return parsedJson as T;
}

export const api = {
  listCameras: (): Promise<Camera[]> =>
    apiRequest("/api/cameras", { method: "GET" }, cameraListSchema),

  getCamera: (id: number): Promise<Camera> =>
    apiRequest(`/api/cameras/${id}`, { method: "GET" }, cameraReadSchema),

  createCamera: (data: CameraFormData): Promise<Camera> =>
    apiRequest(
      "/api/cameras",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      },
      cameraReadSchema
    ),

  updateCamera: (id: number, data: Partial<CameraFormData>): Promise<Camera> =>
    apiRequest(
      `/api/cameras/${id}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      },
      cameraReadSchema
    ),

  deleteCamera: (id: number): Promise<void> =>
    apiRequest(`/api/cameras/${id}`, { method: "DELETE" }),

  importCameras: async (
    file: File,
    dryRun: boolean
  ): Promise<CameraImportPreview | CameraImportSuccess> => {
    if (dryRun) {
      return apiRequest<CameraImportPreview>(
        "/api/cameras/import?dry_run=true",
        {
          method: "POST",
          headers: { "Content-Type": "text/csv" },
          body: file,
        },
        cameraImportPreviewSchema
      );
    }
    return apiRequest<CameraImportSuccess>(
      "/api/cameras/import?dry_run=false",
      {
        method: "POST",
        headers: { "Content-Type": "text/csv" },
        body: file,
      },
      cameraImportSuccessSchema
    );
  },
};
