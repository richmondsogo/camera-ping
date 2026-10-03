import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import type { CameraRead } from "@/lib/schemas";

import {
  ALL_LOCATIONS_VALUE,
  filterCameras,
  formatLastChecked,
  getDistinctLocations,
  locationToSelectValue,
  mapServerErrors,
  selectValueToLocation,
} from "./utils";

describe("formatLastChecked", () => {
  it("returns 'Never' when isoString is null or undefined", () => {
    const fromNull = formatLastChecked(null);
    expect(fromNull.text).toBe("Never");
    expect(fromNull.title).toBe("Never");
    expect(fromNull.toString()).toBe("Never");

    const fromUndefined = formatLastChecked(undefined);
    expect(fromUndefined.text).toBe("Never");
  });

  it("formats midnight as 00:00:00 (never 24:00:00)", () => {
    // 2026-10-03 midnight UTC
    const formatted = formatLastChecked("2026-10-03T00:00:00.000Z", "UTC");
    expect(formatted.text).toBe("2026-10-03 00:00:00");
    expect(formatted.title).toContain("UTC");
    expect(formatted.title).toBe("2026-10-03 00:00:00 (UTC)");
  });

  it("formats dates in a DST-change week correctly with timezone in title", () => {
    // In America/New_York, DST transitions on 2026-11-01 at 02:00
    // Test a date during that week
    const beforeDst = formatLastChecked(
      "2026-10-31T16:00:00.000Z",
      "America/New_York"
    );
    // 16:00 UTC - 4 hrs = 12:00 EDT
    expect(beforeDst.text).toBe("2026-10-31 12:00:00");
    expect(beforeDst.title).toContain("America/New_York");

    const afterDst = formatLastChecked(
      "2026-11-02T17:00:00.000Z",
      "America/New_York"
    );
    // 17:00 UTC - 5 hrs = 12:00 EST
    expect(afterDst.text).toBe("2026-11-02 12:00:00");
    expect(afterDst.title).toContain("America/New_York");
  });

  it("handles invalid date strings gracefully", () => {
    const formatted = formatLastChecked("not-a-date");
    expect(formatted.text).toBe("Invalid date");
  });
});

describe("Location select sentinel and conversion", () => {
  it("converts null to the sentinel and back", () => {
    const sentinel = locationToSelectValue(null);
    expect(sentinel).toBe(ALL_LOCATIONS_VALUE);
    expect(sentinel).toContain("\x00"); // control character safe from real locations
    expect(selectValueToLocation(sentinel)).toBeNull();
  });

  it("preserves real locations including 'all', 'All', and '__ALL__'", () => {
    for (const loc of ["all", "All", "__ALL__", "Warehouse", "Gate 1"]) {
      const val = locationToSelectValue(loc);
      expect(val).toBe(loc);
      expect(selectValueToLocation(val)).toBe(loc);
    }
  });
});

describe("filterCameras", () => {
  const sampleCameras: CameraRead[] = [
    {
      id: 1,
      camera_name: "Front Gate Alpha",
      location: "all",
      description: "Main entrance primary PTZ",
      ip_address: "192.0.2.10",
      status: "online",
      last_checked: "2026-10-03T10:00:00Z",
      last_online: "2026-10-03T10:00:00Z",
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-01T00:00:00Z",
    },
    {
      id: 2,
      camera_name: "Side Gate Beta",
      location: "All",
      description: "Employee turnstile camera",
      ip_address: "192.0.2.20",
      status: "offline",
      last_checked: "2026-10-03T10:00:00Z",
      last_online: null,
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-01T00:00:00Z",
    },
    {
      id: 3,
      camera_name: "Back Dock Gamma",
      location: "__ALL__",
      description: "Loading dock south",
      ip_address: "192.0.2.30",
      status: "unknown",
      last_checked: null,
      last_online: null,
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-01T00:00:00Z",
    },
    {
      id: 4,
      camera_name: "Roof Camera",
      location: "Server Room",
      description: "Roof panoramic view",
      ip_address: "192.0.2.40",
      status: "online",
      last_checked: "2026-10-03T10:00:00Z",
      last_online: "2026-10-03T10:00:00Z",
      created_at: "2026-10-01T00:00:00Z",
      updated_at: "2026-10-01T00:00:00Z",
    },
  ];

  it("filters with null location matching all cameras", () => {
    const result = filterCameras(sampleCameras, "", "all", null);
    expect(result).toHaveLength(4);
  });

  it("distinguishes locations named 'all', 'All', and '__ALL__'", () => {
    const matchLower = filterCameras(sampleCameras, "", "all", "all");
    expect(matchLower.map((c) => c.id)).toEqual([1]);

    const matchUpper = filterCameras(sampleCameras, "", "all", "All");
    expect(matchUpper.map((c) => c.id)).toEqual([2]);

    const matchDunder = filterCameras(sampleCameras, "", "all", "__ALL__");
    expect(matchDunder.map((c) => c.id)).toEqual([3]);
  });

  it("filters by status (online, offline, unknown)", () => {
    expect(
      filterCameras(sampleCameras, "", "online", null).map((c) => c.id)
    ).toEqual([1, 4]);
    expect(
      filterCameras(sampleCameras, "", "offline", null).map((c) => c.id)
    ).toEqual([2]);
    expect(
      filterCameras(sampleCameras, "", "unknown", null).map((c) => c.id)
    ).toEqual([3]);
  });

  it("searches case-insensitively across name, location, description, and IP", () => {
    // Search by IP
    expect(
      filterCameras(sampleCameras, "192.0.2.20", "all", null).map((c) => c.id)
    ).toEqual([2]);
    // Search by partial name (case-insensitive)
    expect(
      filterCameras(sampleCameras, "beta", "all", null).map((c) => c.id)
    ).toEqual([2]);
    // Search by partial description
    expect(
      filterCameras(sampleCameras, "loading", "all", null).map((c) => c.id)
    ).toEqual([3]);
    // Search by partial location
    expect(
      filterCameras(sampleCameras, "server", "all", null).map((c) => c.id)
    ).toEqual([4]);
    // Trimmed whitespace in query
    expect(
      filterCameras(sampleCameras, "   roof   ", "all", null).map((c) => c.id)
    ).toEqual([4]);
  });
});

describe("getDistinctLocations", () => {
  it("extracts unique non-null locations sorted case-insensitively", () => {
    const cameras: CameraRead[] = [
      {
        id: 1,
        camera_name: "Cam 1",
        location: "Warehouse",
        description: "",
        ip_address: "192.0.2.1",
        status: "online",
        last_checked: null,
        last_online: null,
        created_at: "",
        updated_at: "",
      },
      {
        id: 2,
        camera_name: "Cam 2",
        location: "all",
        description: "",
        ip_address: "192.0.2.2",
        status: "online",
        last_checked: null,
        last_online: null,
        created_at: "",
        updated_at: "",
      },
      {
        id: 3,
        camera_name: "Cam 3",
        location: "",
        description: "",
        ip_address: "192.0.2.3",
        status: "online",
        last_checked: null,
        last_online: null,
        created_at: "",
        updated_at: "",
      },
      {
        id: 4,
        camera_name: "Cam 4",
        location: "building a",
        description: "",
        ip_address: "192.0.2.4",
        status: "online",
        last_checked: null,
        last_online: null,
        created_at: "",
        updated_at: "",
      },
      {
        id: 5,
        camera_name: "Cam 5",
        location: "Building A",
        description: "",
        ip_address: "192.0.2.5",
        status: "online",
        last_checked: null,
        last_online: null,
        created_at: "",
        updated_at: "",
      },
    ];

    const locations = getDistinctLocations(cameras);
    expect(locations).toContain("Warehouse");
    expect(locations).toContain("all");
    expect(locations).toContain("building a");
    expect(locations).not.toContain(null);
  });
});

describe("mapServerErrors", () => {
  it("maps network errors to standard message", () => {
    const err = new ApiError({
      kind: "network",
      status: 0,
      message: "Failed to fetch",
    });
    const result = mapServerErrors(err);
    expect(result.formError).toBe("Couldn't reach the server. Try again.");
    expect(result.fieldErrors).toEqual({});
  });

  it("maps server errors (5xx / empty body / non-JSON) to standard message", () => {
    const err = new ApiError({
      kind: "server",
      status: 500,
      message: "Server error",
    });
    const result = mapServerErrors(err);
    expect(result.formError).toBe("Couldn't reach the server. Try again.");
    expect(result.fieldErrors).toEqual({});
  });

  it("maps invalid-response errors to standard message", () => {
    const err = new ApiError({
      kind: "invalid-response",
      status: 200,
      message: "Validation failed",
    });
    const result = mapServerErrors(err);
    expect(result.formError).toBe("Couldn't reach the server. Try again.");
    expect(result.fieldErrors).toEqual({});
  });

  it("maps 409 duplicate IP error to field error", () => {
    const err = new ApiError({
      kind: "http",
      status: 409,
      message: "Conflict",
      detail: [
        {
          loc: ["body", "ip_address"],
          msg: "A camera with this IP address already exists.",
          type: "duplicate",
        },
      ],
    });
    const result = mapServerErrors(err);
    expect(result.formError).toBeNull();
    expect(result.fieldErrors.ip_address).toBe(
      "A camera with this IP address already exists."
    );
  });

  it("maps 422 validation errors to corresponding field errors", () => {
    const err = new ApiError({
      kind: "http",
      status: 422,
      message: "Unprocessable Entity",
      detail: [
        {
          loc: ["body", "camera_name"],
          msg: "Camera name cannot be empty.",
          type: "value_error",
        },
        {
          loc: ["body", "ip_address"],
          msg: "Invalid IP address format.",
          type: "value_error",
        },
      ],
    });
    const result = mapServerErrors(err);
    expect(result.formError).toBeNull();
    expect(result.fieldErrors.camera_name).toBe("Camera name cannot be empty.");
    expect(result.fieldErrors.ip_address).toBe("Invalid IP address format.");
  });

  it("handles string detail in 409 error", () => {
    const err = new ApiError({
      kind: "http",
      status: 409,
      message: "Conflict",
      detail: "A camera with this IP address already exists.",
    });
    const result = mapServerErrors(err);
    expect(result.fieldErrors.ip_address).toBe(
      "A camera with this IP address already exists."
    );
  });

  it("handles loc items with numbers and strings and extra total_errors key without breaking mapServerErrors", () => {
    const errorBody = {
      detail: [
        {
          loc: ["file", 7, "ip_address"],
          msg: "x",
          type: "value_error",
        },
      ],
      total_errors: 1,
    };
    const err = new ApiError({
      kind: "http",
      status: 422,
      message: "x",
      detail: errorBody.detail,
      totalErrors: errorBody.total_errors,
    });
    const result = mapServerErrors(err);
    expect(result.formError).toBeNull();
    expect(result.fieldErrors.ip_address).toBe("x");
  });

  it("maps unknown non-ApiError to generic error", () => {
    const result = mapServerErrors(new Error("Random failure"));
    expect(result.formError).toBe("An unexpected error occurred.");
    expect(result.fieldErrors).toEqual({});
  });
});
