import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

describe("api and ApiError", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("handles 204 No Content without parsing JSON body", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(null, {
        status: 204,
      })
    );

    const result = await api.deleteCamera(1);
    expect(result).toBeUndefined();
  });

  it("converts thrown network exceptions into ApiError kind 'network'", async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(api.listCameras()).rejects.toThrow(ApiError);
    await api.listCameras().catch((err: ApiError) => {
      expect(err.kind).toBe("network");
      expect(err.status).toBe(0);
      expect(err.message).toBe("Couldn't reach the server. Try again.");
    });
  });

  it("converts empty-body 500 into ApiError kind 'server'", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response("", {
        status: 500,
        headers: { "Content-Type": "text/plain" },
      })
    );

    await expect(api.listCameras()).rejects.toThrow(ApiError);
    await api.listCameras().catch((err: ApiError) => {
      expect(err.kind).toBe("server");
      expect(err.status).toBe(500);
      expect(err.message).toBe("Couldn't reach the server. Try again.");
    });
  });

  it("converts non-JSON 502/503/504 proxy errors into ApiError kind 'server'", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response("<html>Bad Gateway</html>", {
        status: 502,
        headers: { "Content-Type": "text/html" },
      })
    );

    await expect(api.listCameras()).rejects.toThrow(ApiError);
    await api.listCameras().catch((err: ApiError) => {
      expect(err.kind).toBe("server");
      expect(err.status).toBe(502);
      expect(err.message).toBe("Couldn't reach the server. Try again.");
    });
  });

  it("converts 404 string detail into ApiError kind 'http'", async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Camera not found." }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      })
    );

    await api.getCamera(99).catch((err: ApiError) => {
      expect(err.kind).toBe("http");
      expect(err.status).toBe(404);
      expect(err.detail).toBe("Camera not found.");
      expect(err.message).toBe("Camera not found.");
    });
  });

  it("converts 409/422 array detail into ApiError kind 'http'", async () => {
    const detailPayload = [
      {
        loc: ["body", "ip_address"],
        msg: "A camera with this IP address already exists.",
        type: "duplicate",
      },
    ];

    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: detailPayload }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      })
    );

    await api
      .createCamera({
        camera_name: "Test",
        location: "Loc",
        description: "Desc",
        ip_address: "192.0.2.10",
      })
      .catch((err: ApiError) => {
        expect(err.kind).toBe("http");
        expect(err.status).toBe(409);
        expect(err.detail).toEqual(detailPayload);
        expect(err.message).toBe(
          "A camera with this IP address already exists."
        );
      });
  });

  it("converts schema validation failure on success response into ApiError kind 'invalid-response'", async () => {
    // Malformed camera response missing id
    const malformedPayload = {
      camera_name: "Malformed",
    };

    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(malformedPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    await api.getCamera(1).catch((err: ApiError) => {
      expect(err.kind).toBe("invalid-response");
      expect(err.status).toBe(200);
      expect(err.message).toBe("Invalid response received from server.");
    });
  });

  it("returns parsed data when schema passes", async () => {
    const validCamera = {
      id: 1,
      camera_name: "Front Gate",
      location: "Main",
      description: "Front gate",
      ip_address: "192.0.2.10",
      status: "online",
      consecutive_failures: 0,
      last_checked: null,
      last_online: null,
      created_at: "2026-10-03T10:00:00Z",
      updated_at: "2026-10-03T10:00:00Z",
    };

    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(validCamera), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const result = await api.getCamera(1);
    expect(result).toEqual(validCamera);
  });

  it("calls getMonitoringStatus, startMonitoring, and stopMonitoring with schemas", async () => {
    const mockStatus = {
      running: true,
      interval_seconds: 60,
      running_since: "2026-10-01T10:00:00Z",
      last_cycle_started_at: "2026-10-01T10:01:00Z",
      last_cycle_finished_at: "2026-10-01T10:01:05Z",
      next_check_at: "2026-10-01T10:02:00Z",
      total: 5,
      online: 4,
      offline: 1,
      unknown: 0,
    };

    global.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(mockStatus), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    const getRes = await api.getMonitoringStatus();
    expect(getRes).toEqual(mockStatus);

    const startRes = await api.startMonitoring();
    expect(startRes).toEqual(mockStatus);

    const stopRes = await api.stopMonitoring();
    expect(stopRes).toEqual(mockStatus);
  });

  it("handles loc items that are string or number and preserves total_errors without breaking mapServerErrors", async () => {
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

    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(errorBody), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      })
    );

    let caughtError: ApiError | null = null;
    try {
      await api.listCameras();
    } catch (err) {
      caughtError = err as ApiError;
    }

    expect(caughtError).not.toBeNull();
    expect(caughtError?.status).toBe(422);
    expect(caughtError?.totalErrors).toBe(1);
    expect(caughtError?.detail).toEqual(errorBody.detail);
  });
});
