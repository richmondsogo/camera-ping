import * as React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { CameraToolbar } from "./CameraToolbar";
import { DashboardPage } from "@/pages/DashboardPage";
import { api } from "@/lib/api";
import type { CameraRead } from "@/lib/schemas";

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return {
    queryClient,
    ...render(
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    ),
  };
}

describe("CameraToolbar filter select labels and clear filters", () => {
  it("displays 'All Statuses' by default on Status trigger and displays 'Online' when selected", () => {
    function ControlledStatus() {
      const [status, setStatus] = React.useState<
        "all" | "online" | "offline" | "unknown"
      >("all");
      return (
        <CameraToolbar
          searchQuery=""
          onSearchChange={() => {}}
          statusFilter={status}
          onStatusChange={setStatus}
          locationFilter={null}
          onLocationChange={() => {}}
          distinctLocations={["HQ"]}
          totalCameras={5}
          filteredCameras={5}
          onAddCamera={() => {}}
        />
      );
    }

    render(<ControlledStatus />);
    const trigger = screen.getByTestId("status-filter-trigger");
    expect(trigger).toHaveTextContent("All Statuses");

    // Click trigger to open popup
    fireEvent.click(trigger);
    const onlineOption = screen.getByRole("option", { name: "Online" });
    fireEvent.pointerDown(onlineOption);
    fireEvent.click(onlineOption);

    expect(trigger).toHaveTextContent("Online");
  });

  it("displays 'All Locations' by default on Location trigger and displays chosen location", () => {
    function ControlledLocation() {
      const [loc, setLoc] = React.useState<string | null>(null);
      return (
        <CameraToolbar
          searchQuery=""
          onSearchChange={() => {}}
          statusFilter="all"
          onStatusChange={() => {}}
          locationFilter={loc}
          onLocationChange={setLoc}
          distinctLocations={["Server Room", "Main Gate"]}
          totalCameras={5}
          filteredCameras={5}
          onAddCamera={() => {}}
        />
      );
    }

    render(<ControlledLocation />);
    const trigger = screen.getByTestId("location-filter-trigger");
    expect(trigger).toHaveTextContent("All Locations");

    fireEvent.click(trigger);
    const serverRoomOption = screen.getByRole("option", {
      name: "Server Room",
    });
    fireEvent.pointerDown(serverRoomOption);
    fireEvent.click(serverRoomOption);

    expect(trigger).toHaveTextContent("Server Room");
  });

  it("locations literally named 'all', 'All', and '__ALL_LOCATIONS__' display their own names", () => {
    function LiteralLocations() {
      const [loc, setLoc] = React.useState<string | null>(null);
      return (
        <div>
          <button data-testid="set-literal-all" onClick={() => setLoc("all")}>
            Set all
          </button>
          <button data-testid="set-literal-All" onClick={() => setLoc("All")}>
            Set All
          </button>
          <button
            data-testid="set-literal-sentinel"
            onClick={() => setLoc("__ALL_LOCATIONS__")}
          >
            Set sentinel
          </button>
          <button data-testid="set-literal-null" onClick={() => setLoc(null)}>
            Set null
          </button>
          <CameraToolbar
            searchQuery=""
            onSearchChange={() => {}}
            statusFilter="all"
            onStatusChange={() => {}}
            locationFilter={loc}
            onLocationChange={setLoc}
            distinctLocations={["all", "All", "__ALL_LOCATIONS__"]}
            totalCameras={10}
            filteredCameras={10}
            onAddCamera={() => {}}
          />
        </div>
      );
    }

    render(<LiteralLocations />);
    const trigger = screen.getByTestId("location-filter-trigger");
    expect(trigger).toHaveTextContent("All Locations");

    // When locationFilter is "all"
    fireEvent.click(screen.getByTestId("set-literal-all"));
    expect(trigger).toHaveTextContent("all");
    expect(trigger).not.toHaveTextContent("All Locations");

    // When locationFilter is "All"
    fireEvent.click(screen.getByTestId("set-literal-All"));
    expect(trigger).toHaveTextContent("All");

    // When locationFilter is "__ALL_LOCATIONS__"
    fireEvent.click(screen.getByTestId("set-literal-sentinel"));
    expect(trigger).toHaveTextContent("__ALL_LOCATIONS__");
    expect(trigger).not.toHaveTextContent("All Locations");

    // When locationFilter is null (All Locations)
    fireEvent.click(screen.getByTestId("set-literal-null"));
    expect(trigger).toHaveTextContent("All Locations");
  });

  it("Clear filters button appears only when a filter is active, and clicking it restores the full list", async () => {
    const testCameras: CameraRead[] = [
      {
        id: 1,
        camera_name: "Cam Alpha",
        ip_address: "192.0.2.10",
        location: "Warehouse",
        description: "Zone 1",
        status: "online",
        consecutive_failures: 0,
        last_checked: null,
        last_online: null,
        created_at: "2026-10-01T10:00:00Z",
        updated_at: "2026-10-01T10:00:00Z",
      },
      {
        id: 2,
        camera_name: "Cam Beta",
        ip_address: "192.0.2.20",
        location: "Office",
        description: "Zone 2",
        status: "offline",
        consecutive_failures: 0,
        last_checked: null,
        last_online: null,
        created_at: "2026-10-01T10:00:00Z",
        updated_at: "2026-10-01T10:00:00Z",
      },
    ];

    vi.spyOn(api, "listCameras").mockResolvedValue(testCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Cam Alpha")).toBeInTheDocument();
      expect(screen.getByText("Cam Beta")).toBeInTheDocument();
    });

    // Initially, no Clear filters button is visible
    expect(
      screen.queryByTestId("clear-filters-toolbar-button")
    ).not.toBeInTheDocument();

    // Type in search input to activate filter
    const searchInput = screen.getByTestId("camera-search-input");
    fireEvent.change(searchInput, { target: { value: "Alpha" } });

    // Now Clear filters button must be visible
    const clearButton = await screen.findByTestId(
      "clear-filters-toolbar-button"
    );
    expect(clearButton).toBeInTheDocument();

    // Only Alpha is showing
    expect(screen.getByText("Cam Alpha")).toBeInTheDocument();
    expect(screen.queryByText("Cam Beta")).toBeNull();

    // Click Clear filters
    fireEvent.click(clearButton);

    // Filter is reset, button disappears, full list restored
    await waitFor(() => {
      expect(screen.getByText("Cam Alpha")).toBeInTheDocument();
      expect(screen.getByText("Cam Beta")).toBeInTheDocument();
      expect(
        screen.queryByTestId("clear-filters-toolbar-button")
      ).not.toBeInTheDocument();
    });
    expect(searchInput).toHaveValue("");
  });

  it("Clear filters button inside 'No cameras match the current filters' state restores the full list", async () => {
    const testCameras: CameraRead[] = [
      {
        id: 1,
        camera_name: "Cam Alpha",
        ip_address: "192.0.2.10",
        location: "Warehouse",
        description: "Zone 1",
        status: "online",
        consecutive_failures: 0,
        last_checked: null,
        last_online: null,
        created_at: "2026-10-01T10:00:00Z",
        updated_at: "2026-10-01T10:00:00Z",
      },
    ];

    vi.spyOn(api, "listCameras").mockResolvedValue(testCameras);

    renderWithClient(<DashboardPage pollInterval={false} />);

    await waitFor(() => {
      expect(screen.getByText("Cam Alpha")).toBeInTheDocument();
    });

    // Filter by impossible query
    const searchInput = screen.getByTestId("camera-search-input");
    fireEvent.change(searchInput, { target: { value: "NonExistent" } });

    await waitFor(() => {
      expect(
        screen.getByTestId("filtered-empty-cameras-state")
      ).toBeInTheDocument();
    });

    const tableClearBtn = screen.getByTestId("table-clear-filters-button");
    expect(tableClearBtn).toBeInTheDocument();

    // Click Clear filters in empty state table
    fireEvent.click(tableClearBtn);

    await waitFor(() => {
      expect(screen.getByText("Cam Alpha")).toBeInTheDocument();
      expect(
        screen.queryByTestId("filtered-empty-cameras-state")
      ).not.toBeInTheDocument();
    });
    expect(searchInput).toHaveValue("");
  });
});
