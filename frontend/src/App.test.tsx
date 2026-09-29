import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App Shell & Routing", () => {
  it("renders the header with app name and navigation", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

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
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );

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
