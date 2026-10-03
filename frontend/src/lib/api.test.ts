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
});
