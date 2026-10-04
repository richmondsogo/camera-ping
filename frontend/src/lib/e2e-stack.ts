/**
 * E2E Stack Isolation and Safety Guards.
 *
 * Prevents accidental execution of destructive reset or seed actions
 * against developer (8000, 5173) or production databases.
 */

export const DEFAULT_E2E_BACKEND_PORT = 18000;

export function getExpectedE2eBackendPort(): number {
  if (typeof process !== "undefined" && process.env?.E2E_BACKEND_PORT) {
    const parsed = Number.parseInt(process.env.E2E_BACKEND_PORT, 10);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }
  return DEFAULT_E2E_BACKEND_PORT;
}

export function assertE2eStack(apiUrlOrPort: string | number): void {
  const expectedPort = getExpectedE2eBackendPort();
  let port: number;

  if (typeof apiUrlOrPort === "number") {
    port = apiUrlOrPort;
  } else {
    try {
      const url = new URL(
        apiUrlOrPort.startsWith("http://") ||
          apiUrlOrPort.startsWith("https://")
          ? apiUrlOrPort
          : `http://${apiUrlOrPort}`
      );
      port = url.port
        ? Number.parseInt(url.port, 10)
        : url.protocol === "https:"
          ? 443
          : 80;
    } catch {
      throw new Error(
        `Invalid URL or port provided to assertE2eStack: ${apiUrlOrPort}`
      );
    }
  }

  if (port === 8000 || port === 5173) {
    throw new Error(
      `Refusing to run destructive e2e action against protected production/development port ${port}. Only e2e port ${expectedPort} is permitted.`
    );
  }

  if (port !== expectedPort) {
    throw new Error(
      `Target port ${port} does not match configured e2e backend port ${expectedPort}. Destructive e2e actions are prohibited.`
    );
  }
}

export interface SeedCameraPayload {
  camera_name: string;
  location: string;
  description: string;
  ip_address: string;
}

const SEED_LOCATIONS = [
  "Main Gate",
  "Warehouse",
  "Office Lobby",
  "Parking Lot",
  "Loading Dock",
  "Perimeter Fence",
];

const SEED_DESCRIPTIONS = [
  "Optical camera covering main visitor turnstile.",
  "High-resolution dome camera with infrared night vision and wide dynamic range.",
  "Fixed camera focused on delivery bay entrance and loading ramps.",
  "Corridor view.",
  "Overhead wide-angle monitoring of employee entrance and vehicle checkpoint.",
];

export const LONG_SEED_LOCATION =
  "Perimeter West Boundary - Critical Infrastructure Sector 9 Storage Vault";

export function generateSeedCameras(count: number): SeedCameraPayload[] {
  const cameras: SeedCameraPayload[] = [];
  for (let i = 1; i <= count; i++) {
    const loc =
      i === 30
        ? LONG_SEED_LOCATION
        : SEED_LOCATIONS[(i - 1) % SEED_LOCATIONS.length];
    const desc = SEED_DESCRIPTIONS[(i - 1) % SEED_DESCRIPTIONS.length];
    cameras.push({
      camera_name: `Camera ${String(i).padStart(2, "0")} - ${loc}`,
      location: loc,
      description: `${desc} (Unit #${i})`,
      ip_address: `192.0.2.${i}`,
    });
  }
  return cameras;
}

export async function stopMonitoring(
  apiBaseUrl: string = `http://127.0.0.1:${getExpectedE2eBackendPort()}`
): Promise<void> {
  assertE2eStack(apiBaseUrl);
  try {
    await fetch(`${apiBaseUrl}/api/monitoring/stop`, { method: "POST" });
  } catch {
    // ignore if already stopped or network unready
  }
}

export async function resetCameras(
  apiBaseUrl: string = `http://127.0.0.1:${getExpectedE2eBackendPort()}`
): Promise<void> {
  assertE2eStack(apiBaseUrl);

  await stopMonitoring(apiBaseUrl);

  const getRes = await fetch(`${apiBaseUrl}/api/cameras`);
  if (!getRes.ok) {
    throw new Error(
      `Failed to list cameras during resetCameras: HTTP ${getRes.status}`
    );
  }
  const cameras: Array<{ id: number }> = await getRes.json();

  for (const camera of cameras) {
    const delRes = await fetch(`${apiBaseUrl}/api/cameras/${camera.id}`, {
      method: "DELETE",
    });
    if (!delRes.ok && delRes.status !== 404) {
      throw new Error(
        `Failed to delete camera ${camera.id} during resetCameras: HTTP ${delRes.status}`
      );
    }
  }
}

export async function seedCameras(
  count: number,
  apiBaseUrl: string = `http://127.0.0.1:${getExpectedE2eBackendPort()}`
): Promise<SeedCameraPayload[]> {
  assertE2eStack(apiBaseUrl);

  const payloads = generateSeedCameras(count);
  for (const payload of payloads) {
    const res = await fetch(`${apiBaseUrl}/api/cameras`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(
        `Failed to seed camera ${payload.camera_name}: HTTP ${res.status} - ${errText}`
      );
    }
  }
  return payloads;
}
