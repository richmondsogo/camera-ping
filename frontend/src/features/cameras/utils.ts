import { ApiError } from "@/lib/api";
import type { CameraRead, CameraStatus } from "@/lib/schemas";

export const ALL_LOCATIONS_VALUE = "\x00__ALL_LOCATIONS__";

export function locationToSelectValue(location: string | null): string {
  return location === null ? ALL_LOCATIONS_VALUE : location;
}

export function selectValueToLocation(value: string): string | null {
  return value === ALL_LOCATIONS_VALUE ? null : value;
}

export interface FormattedLastChecked {
  text: string;
  title: string;
  toString(): string;
}

/**
 * Formats a last_checked ISO string using Intl.DateTimeFormat.formatToParts
 * with hourCycle: "h23".
 * Returns "Never" if isoString is null/undefined.
 * Title includes the resolved timezone name.
 */
export function formatLastChecked(
  isoString: string | null | undefined,
  timeZone?: string
): FormattedLastChecked {
  if (!isoString) {
    return {
      text: "Never",
      title: "Never",
      toString() {
        return "Never";
      },
    };
  }

  const date = new Date(isoString);
  if (isNaN(date.getTime())) {
    return {
      text: "Invalid date",
      title: "Invalid date",
      toString() {
        return "Invalid date";
      },
    };
  }

  const dtf = new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
    ...(timeZone ? { timeZone } : {}),
  });

  const parts = dtf.formatToParts(date);
  const p: Record<string, string> = {};
  for (const part of parts) {
    p[part.type] = part.value;
  }

  const text = `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
  const resolvedTz = dtf.resolvedOptions().timeZone;
  const title = `${text} (${resolvedTz})`;

  return {
    text,
    title,
    toString() {
      return text;
    },
  };
}

export type StatusFilter = CameraStatus | "all";

/**
 * Filters camera list by search query (case-insensitive substring across name,
 * location, description, and IP), status, and location.
 */
export function filterCameras(
  cameras: CameraRead[],
  query: string,
  statusFilter: StatusFilter,
  locationFilter: string | null
): CameraRead[] {
  const q = query.trim().toLowerCase();

  return cameras.filter((camera) => {
    // 1. Text search
    if (q.length > 0) {
      const matchName = camera.camera_name.toLowerCase().includes(q);
      const matchLocation = (camera.location ?? "").toLowerCase().includes(q);
      const matchDescription = (camera.description ?? "")
        .toLowerCase()
        .includes(q);
      const matchIp = camera.ip_address.toLowerCase().includes(q);
      if (!matchName && !matchLocation && !matchDescription && !matchIp) {
        return false;
      }
    }

    // 2. Status filter
    if (statusFilter !== "all") {
      if (camera.status !== statusFilter) {
        return false;
      }
    }

    // 3. Location filter (null means All)
    if (locationFilter !== null) {
      if (camera.location !== locationFilter) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Returns distinct non-null, non-empty locations sorted case-insensitively.
 */
export function getDistinctLocations(cameras: CameraRead[]): string[] {
  const set = new Set<string>();
  for (const camera of cameras) {
    if (camera.location && camera.location.trim().length > 0) {
      set.add(camera.location.trim());
    }
  }
  return Array.from(set).sort((a, b) =>
    a.localeCompare(b, undefined, { sensitivity: "base" })
  );
}

export interface MappedErrors {
  formError: string | null;
  fieldErrors: Record<string, string>;
}

/**
 * Maps server errors (network, server, 409, 422) to form error messages and
 * field-level errors.
 */
export function mapServerErrors(error: unknown): MappedErrors {
  if (error instanceof ApiError) {
    if (error.kind === "network" || error.kind === "server") {
      return {
        formError: "Couldn't reach the server. Try again.",
        fieldErrors: {},
      };
    }

    if (error.kind === "invalid-response") {
      return {
        formError: "Couldn't reach the server. Try again.",
        fieldErrors: {},
      };
    }

    if (error.kind === "http") {
      const fieldErrors: Record<string, string> = {};
      let formError: string | null = null;

      const detail = error.detail;
      if (Array.isArray(detail)) {
        for (const item of detail) {
          if (
            item &&
            typeof item === "object" &&
            Array.isArray(item.loc) &&
            item.loc.length > 0
          ) {
            const fieldName = String(item.loc[item.loc.length - 1]);
            const message = String(item.msg ?? "Invalid value");
            fieldErrors[fieldName] = message;
          } else if (item && typeof item === "object" && item.msg) {
            formError = String(item.msg);
          }
        }
      } else if (typeof detail === "string") {
        if (error.status === 409 && detail.toLowerCase().includes("ip")) {
          fieldErrors.ip_address = detail;
        } else {
          formError = detail;
        }
      }

      if (error.status === 409 && Object.keys(fieldErrors).length === 0) {
        fieldErrors.ip_address =
          "A camera with this IP address already exists.";
      }

      return { formError, fieldErrors };
    }
  }

  return {
    formError: "An unexpected error occurred.",
    fieldErrors: {},
  };
}
