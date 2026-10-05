import * as React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "@/pages/DashboardPage";
import { api } from "@/lib/api";
import type { CameraRead, MonitoringStatus } from "@/lib/schemas";

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    ),
  };
}

const mockCamerasWithOffline: CameraRead[] = [
  {
    id: 1,
    camera_name: "Gate Cam",
    ip_address: "192.0.2.10",
    location: "Entrance",
    description: "Main gate",
    status: "online",
    consecutive_failures: 0,
    last_checked: "2026-10-04T12:00:00Z",
    last_online: "2026-10-04T12:00:00Z",
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
  },
  {
    id: 2,
    camera_name: "Dock Cam",
    ip_address: "192.0.2.20",
    location: "Dock",
    description: "Loading dock",
    status: "offline",
    consecutive_failures: 5,
    last_checked: "2026-10-04T12:00:00Z",
    last_online: "2026-10-04T11:00:00Z",
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
  },
];

const mockStoppedStatus: MonitoringStatus = {
  running: false,
  interval_seconds: 60,
  last_cycle_started_at: null,
  last_cycle_finished_at: null,
  next_check_at: null,
  running_since: null,
  total: 2,
  online: 1,
  offline: 1,
  unknown: 0,
};

const mockRunningStatus: MonitoringStatus = {
  running: true,
  interval_seconds: 60,
  last_cycle_started_at: "2026-10-04T12:00:00Z",
  last_cycle_finished_at: "2026-10-04T12:00:01Z",
  next_check_at: "2026-10-04T12:01:00Z",
  running_since: "2026-10-04T11:59:00Z",
  total: 2,
  online: 1,
  offline: 1,
  unknown: 0,
};

describe("DashboardPage monitoring integration", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    document.title = "Camera Monitor";
  });

  it("updates document.title with offline count and restores on unmount", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCamerasWithOffline);
    vi.spyOn(api, "getMonitoringStatus").mockResolvedValue(mockStoppedStatus);

    const { unmount } = renderWithClient(
      <DashboardPage pollInterval={false} />
    );

    await waitFor(() => {
      expect(document.title).toBe("(1 offline) Camera Monitor");
    });

    unmount();
    expect(document.title).toBe("Camera Monitor");
  });

  it("sets document.title to 'Camera Monitor' when 0 cameras are offline", async () => {
    const allOnlineCameras = [mockCamerasWithOffline[0]];
    vi.spyOn(api, "listCameras").mockResolvedValue(allOnlineCameras);
    vi.spyOn(api, "getMonitoringStatus").mockResolvedValue(mockStoppedStatus);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Gate Cam")).toBeInTheDocument();
    });

    expect(document.title).toBe("Camera Monitor");
  });

  it("renders consecutive failure check count on offline camera rows in CameraTable", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCamerasWithOffline);
    vi.spyOn(api, "getMonitoringStatus").mockResolvedValue(mockStoppedStatus);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Dock Cam")).toBeInTheDocument();
    });

    // Offline row should have check count with title attribute
    const checkCountBadge = screen.getByText("5 checks");
    expect(checkCountBadge).toBeInTheDocument();
    expect(checkCountBadge).toHaveAttribute(
      "title",
      "Failed 5 consecutive checks"
    );

    // Online row should not have check count
    expect(screen.queryByText("0 checks")).not.toBeInTheDocument();
  });

  it("handles Start and Stop monitoring lifecycle via API mutations", async () => {
    let currentStatus = mockStoppedStatus;
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCamerasWithOffline);
    vi.spyOn(api, "getMonitoringStatus").mockImplementation(
      async () => currentStatus
    );
    const startSpy = vi
      .spyOn(api, "startMonitoring")
      .mockImplementation(async () => {
        currentStatus = mockRunningStatus;
        return mockRunningStatus;
      });
    const stopSpy = vi
      .spyOn(api, "stopMonitoring")
      .mockImplementation(async () => {
        currentStatus = mockStoppedStatus;
        return mockStoppedStatus;
      });

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Monitoring stopped")).toBeInTheDocument();
    });

    const startButton = screen.getByTestId("start-monitoring-button");
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(startSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText("Monitoring running")).toBeInTheDocument();
    });

    const stopButton = screen.getByTestId("stop-monitoring-button");
    fireEvent.click(stopButton);

    await waitFor(() => {
      expect(stopSpy).toHaveBeenCalledTimes(1);
      expect(screen.getByText("Monitoring stopped")).toBeInTheDocument();
    });
  });

  it("preserves open dialog form inputs when background query polling refreshes", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCamerasWithOffline);
    vi.spyOn(api, "getMonitoringStatus").mockResolvedValue(mockStoppedStatus);

    const { queryClient } = renderWithClient(
      <DashboardPage pollInterval={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Gate Cam")).toBeInTheDocument();
    });

    // Open Add Camera dialog
    const addBtn = screen.getByTestId("add-camera-toolbar-button");
    fireEvent.click(addBtn);

    const nameInput = await screen.findByTestId("camera-name-input");
    fireEvent.change(nameInput, { target: { value: "Draft Camera Name" } });
    expect(nameInput).toHaveValue("Draft Camera Name");

    // Invalidate queries to simulate background refetch
    await queryClient.invalidateQueries();

    // Verify dialog input is NOT reset
    expect(nameInput).toHaveValue("Draft Camera Name");
  });
});
