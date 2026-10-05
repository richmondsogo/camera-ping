import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "./lib/theme";
import { App } from "./App";

function renderApp(initialEntry = "/") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <App />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("App Shell & Routing", () => {
  it("renders the header with app name and navigation", () => {
    renderApp("/");

    expect(screen.getByText("Camera Monitor")).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Main" })
    ).toBeInTheDocument();

    const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
    const settingsLink = screen.getByRole("link", { name: "Settings" });

    expect(dashboardLink).toBeInTheDocument();
    expect(settingsLink).toBeInTheDocument();
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
    expect(settingsLink).not.toHaveAttribute("aria-current");

    expect(
      screen.getByRole("heading", { level: 1, name: "Dashboard" })
    ).toBeInTheDocument();
  });

  it("navigates between Dashboard and Settings routes", () => {
    renderApp("/");

    const settingsLink = screen.getByRole("link", { name: "Settings" });
    fireEvent.click(settingsLink);

    expect(
      screen.getByRole("heading", { level: 1, name: "Settings" })
    ).toBeInTheDocument();
    expect(settingsLink).toHaveAttribute("aria-current", "page");

    const dashboardLink = screen.getByRole("link", { name: "Dashboard" });
    expect(dashboardLink).not.toHaveAttribute("aria-current");

    fireEvent.click(dashboardLink);
    expect(
      screen.getByRole("heading", { level: 1, name: "Dashboard" })
    ).toBeInTheDocument();
    expect(dashboardLink).toHaveAttribute("aria-current", "page");
  });
});
