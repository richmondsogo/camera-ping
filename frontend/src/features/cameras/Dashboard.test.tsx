import * as React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DashboardPage } from "@/pages/DashboardPage";
import { api, ApiError } from "@/lib/api";
import type { CameraRead } from "@/lib/schemas";

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

const mockCameras: CameraRead[] = [
  {
    id: 1,
    camera_name: "Front Gate Cam",
    ip_address: "192.0.2.10",
    location: "Entrance",
    description: "Monitors main front gate entrance",
    status: "online",
    consecutive_failures: 0,
    last_checked: "2026-10-03T12:00:00Z",
    last_online: "2026-10-03T12:00:00Z",
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
  },
  {
    id: 2,
    camera_name: "Warehouse Cam",
    ip_address: "192.0.2.20",
    location: "Warehouse",
    description: "Covers warehouse loading docks",
    status: "offline",
    consecutive_failures: 0,
    last_checked: "2026-10-03T12:05:00Z",
    last_online: "2026-10-02T10:00:00Z",
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
  },
  {
    id: 3,
    camera_name: "Special Cam",
    ip_address: "192.0.2.30",
    location: "__ALL__",
    description: "Camera in __ALL__ location",
    status: "unknown",
    consecutive_failures: 0,
    last_checked: null,
    last_online: null,
    created_at: "2026-10-01T10:00:00Z",
    updated_at: "2026-10-01T10:00:00Z",
  },
];

describe("DashboardPage component tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders table rows and count line for loaded cameras", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    expect(
      screen.getAllByTestId("loading-cameras-skeleton").length
    ).toBeGreaterThan(0);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
      expect(screen.getByText("Warehouse Cam")).toBeInTheDocument();
      expect(screen.getByText("Special Cam")).toBeInTheDocument();
    });

    expect(screen.getByTestId("camera-count-line")).toHaveTextContent(
      "Showing 3 of 3 cameras"
    );
  });

  it("renders text-only empty state and disables search/filters when 0 cameras exist", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue([]);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByTestId("empty-cameras-state")).toBeInTheDocument();
    });

    expect(screen.getByTestId("empty-cameras-state")).toHaveTextContent(
      "No cameras yet. Add your first camera to start monitoring."
    );

    // Search and filter controls must be disabled
    expect(screen.getByTestId("camera-search-input")).toBeDisabled();
    expect(screen.getByTestId("status-filter-trigger")).toBeDisabled();
    expect(screen.getByTestId("location-filter-trigger")).toBeDisabled();

    // Toolbar Add Camera button must remain enabled
    expect(screen.getByTestId("add-camera-toolbar-button")).not.toBeDisabled();
    expect(screen.getByTestId("camera-count-line")).toHaveTextContent(
      "Showing 0 of 0 cameras"
    );
  });

  it("handles singular count line when 1 camera exists", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue([mockCameras[0]]);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    expect(screen.getByTestId("camera-count-line")).toHaveTextContent(
      "Showing 1 of 1 camera"
    );
  });

  it("renders list error state with Retry on empty-body 500, and Retry works when backend recovers", async () => {
    const listSpy = vi
      .spyOn(api, "listCameras")
      .mockRejectedValueOnce(
        new ApiError({
          kind: "server",
          status: 500,
          message: "Server error (500)",
          detail: null,
        })
      )
      .mockResolvedValue(mockCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByTestId("error-cameras-state")).toBeInTheDocument();
    });
    expect(screen.getByText("Failed to load cameras.")).toBeInTheDocument();

    const retryBtn = screen.getByTestId("retry-cameras-button");
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });
    expect(listSpy).toHaveBeenCalledTimes(2);
  });

  it("background refetch keeps existing table visible without blanking or showing skeleton", async () => {
    let resolveRefetch!: (val: CameraRead[]) => void;
    vi.spyOn(api, "listCameras")
      .mockResolvedValueOnce(mockCameras)
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveRefetch = resolve;
          })
      );

    const { queryClient } = renderWithClient(
      <DashboardPage pollInterval={false} />
    );

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    // Trigger background refetch
    void queryClient.refetchQueries({ queryKey: ["cameras"] });

    // Table must still show existing data and NOT show skeleton
    expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    expect(screen.queryByTestId("loading-cameras-skeleton")).toBeNull();

    // Resolve refetch
    resolveRefetch(mockCameras);
    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });
  });

  it("allows selecting __ALL__ location as a real location distinct from All Locations", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    // Search filter input works
    const searchInput = screen.getByTestId("camera-search-input");
    fireEvent.change(searchInput, { target: { value: "__ALL__" } });

    // Only Special Cam matches
    await waitFor(() => {
      expect(screen.getByText("Special Cam")).toBeInTheDocument();
      expect(screen.queryByText("Front Gate Cam")).toBeNull();
      expect(screen.queryByText("Warehouse Cam")).toBeNull();
      expect(screen.getByTestId("camera-count-line")).toHaveTextContent(
        "Showing 1 of 3 cameras"
      );
    });
  });

  it("shows form-level message on non-JSON 500 inside dialog", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);
    vi.spyOn(api, "createCamera").mockRejectedValue(
      new ApiError({
        kind: "server",
        status: 500,
        message: "Server error (500)",
        detail: null,
      })
    );

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    // Open Add Camera dialog
    fireEvent.click(screen.getByTestId("add-camera-toolbar-button"));
    expect(screen.getByTestId("camera-form-dialog")).toBeInTheDocument();

    // Fill valid form
    fireEvent.change(screen.getByTestId("camera-name-input"), {
      target: { value: "New Camera" },
    });
    fireEvent.change(screen.getByTestId("camera-ip-input"), {
      target: { value: "192.0.2.55" },
    });
    fireEvent.change(screen.getByTestId("camera-location-input"), {
      target: { value: "HQ" },
    });
    fireEvent.change(screen.getByTestId("camera-description-input"), {
      target: { value: "Notes" },
    });

    fireEvent.click(screen.getByTestId("submit-camera-form-button"));

    await waitFor(() => {
      expect(screen.getByTestId("dialog-form-error")).toHaveTextContent(
        "Couldn't reach the server. Try again."
      );
    });
  });

  it("shows IP change warning in edit dialog and toggles back when original IP is re-typed", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    // Open Edit dialog for Front Gate Cam (ip: 192.0.2.10)
    fireEvent.click(screen.getByTestId("edit-camera-1"));
    expect(screen.getByTestId("camera-form-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("camera-ip-input")).toHaveValue("192.0.2.10");
    expect(screen.queryByTestId("ip-change-warning")).toBeNull();

    // Change IP to another address
    fireEvent.change(screen.getByTestId("camera-ip-input"), {
      target: { value: "192.0.2.99" },
    });

    // Warning appears
    expect(screen.getByTestId("ip-change-warning")).toBeInTheDocument();
    expect(screen.getByTestId("ip-change-warning")).toHaveTextContent(
      "Changing the IP address resets this camera's reachability statistics and monitoring history."
    );

    // Type back original IP
    fireEvent.change(screen.getByTestId("camera-ip-input"), {
      target: { value: "192.0.2.10" },
    });

    // Warning disappears
    expect(screen.queryByTestId("ip-change-warning")).toBeNull();
  });

  it("prevents dialog dismissal and double submission while request is pending", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);
    let resolveCreate!: () => void;
    vi.spyOn(api, "createCamera").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = () => resolve({} as CameraRead);
        })
    );

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("add-camera-toolbar-button"));
    expect(screen.getByTestId("camera-form-dialog")).toBeInTheDocument();

    fireEvent.change(screen.getByTestId("camera-name-input"), {
      target: { value: "New Cam" },
    });
    fireEvent.change(screen.getByTestId("camera-ip-input"), {
      target: { value: "192.0.2.88" },
    });
    fireEvent.change(screen.getByTestId("camera-location-input"), {
      target: { value: "Site" },
    });
    fireEvent.change(screen.getByTestId("camera-description-input"), {
      target: { value: "Details" },
    });

    fireEvent.click(screen.getByTestId("submit-camera-form-button"));

    await waitFor(() => {
      expect(screen.getByTestId("submit-camera-form-button")).toBeDisabled();
      expect(screen.getByTestId("cancel-camera-form-button")).toBeDisabled();
    });

    // Pressing Escape while pending must do nothing
    fireEvent.keyDown(screen.getByTestId("camera-form-dialog"), {
      key: "Escape",
    });
    expect(screen.getByTestId("camera-form-dialog")).toBeInTheDocument();

    // Clicking Cancel button while pending is disabled
    fireEvent.click(screen.getByTestId("cancel-camera-form-button"));
    expect(screen.getByTestId("camera-form-dialog")).toBeInTheDocument();

    // Finish request
    resolveCreate();
    await waitFor(() => {
      expect(screen.queryByTestId("camera-form-dialog")).toBeNull();
    });
  });

  it("focus returns to Add Camera button after closing Add dialog", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    const addBtn = screen.getByTestId("add-camera-toolbar-button");
    fireEvent.click(addBtn);

    expect(screen.getByTestId("camera-form-dialog")).toBeInTheDocument();

    const cancelBtn = screen.getByTestId("cancel-camera-form-button");
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(document.activeElement).toBe(addBtn);
    });
    expect(document.activeElement).not.toBe(document.body);
  });

  it("focus returns to that row's Edit button after closing Edit dialog", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Warehouse Cam")).toBeInTheDocument();
    });

    const editBtn = screen.getByTestId("edit-camera-2");
    fireEvent.click(editBtn);

    expect(screen.getByTestId("camera-form-dialog")).toBeInTheDocument();

    const cancelBtn = screen.getByTestId("cancel-camera-form-button");
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(document.activeElement).toBe(editBtn);
    });
    expect(document.activeElement).not.toBe(document.body);
  });

  it("focus returns to next row's Edit button after deleting a camera", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue(mockCameras);
    vi.spyOn(api, "deleteCamera").mockResolvedValue(undefined);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Front Gate Cam")).toBeInTheDocument();
    });

    // Delete Front Gate Cam (index 0, next row is camera 2 Warehouse Cam)
    const deleteBtn = screen.getByTestId("delete-camera-1");
    fireEvent.click(deleteBtn);

    expect(screen.getByTestId("delete-camera-dialog")).toBeInTheDocument();

    const confirmBtn = screen.getByTestId("confirm-delete-camera-button");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(document.activeElement).toBe(screen.getByTestId("edit-camera-2"));
    });
    expect(document.activeElement).not.toBe(document.body);
  });

  it("focus returns to previous row's Edit button after deleting the last row", async () => {
    vi.spyOn(api, "listCameras").mockResolvedValue([
      mockCameras[0],
      mockCameras[1],
    ]);
    vi.spyOn(api, "deleteCamera").mockResolvedValue(undefined);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Warehouse Cam")).toBeInTheDocument();
    });

    // Delete Warehouse Cam (last row index 1, previous row is camera 1 Front Gate Cam)
    const deleteBtn = screen.getByTestId("delete-camera-2");
    fireEvent.click(deleteBtn);

    expect(screen.getByTestId("delete-camera-dialog")).toBeInTheDocument();

    const confirmBtn = screen.getByTestId("confirm-delete-camera-button");
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(document.activeElement).toBe(screen.getByTestId("edit-camera-1"));
    });
    expect(document.activeElement).not.toBe(document.body);
  });
});
