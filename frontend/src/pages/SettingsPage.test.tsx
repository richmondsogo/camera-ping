import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SettingsPage } from "./SettingsPage";
import { ThemeProvider } from "@/lib/theme";
import { api } from "@/lib/api";

function renderSettingsPage() {
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
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <SettingsPage />
        </ThemeProvider>
      </QueryClientProvider>
    ),
  };
}

async function selectOption(trigger: HTMLElement, optionName: string) {
  fireEvent.click(trigger);
  const option = await screen.findByRole("option", { name: optionName });
  fireEvent.pointerDown(option);
  fireEvent.click(option);
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("renders Settings heading, Monitoring section, and Appearance section", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 60,
    });

    renderSettingsPage();

    expect(
      screen.getByRole("heading", { level: 1, name: "Settings" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Monitoring" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Appearance" })
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("interval-preset-select")).toBeInTheDocument();
    });
  });

  it("loads settings and shows preset value", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 120,
    });

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByTestId("interval-preset-select")).toHaveTextContent(
        "2 minutes"
      );
    });

    // Save should be disabled initially (not dirty)
    expect(screen.getByTestId("save-settings-button")).toBeDisabled();
    // Helper text for normal intervals
    expect(
      screen.getByText("How often camera reachability is tested.")
    ).toBeInTheDocument();
  });

  it("shows long-interval warning when effective interval >= 3600 seconds", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 7200, // 2 hours -> custom
    });

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByTestId("long-interval-warning")).toBeInTheDocument();
    });

    expect(screen.getByTestId("long-interval-warning")).toHaveTextContent(
      "Outages may take up to 2 hours to detect."
    );
  });

  it("prefills custom amount and unit when switching to Custom… and remains clean (Amendment 3)", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 60, // 1 minute
    });

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByTestId("interval-preset-select")).toHaveTextContent(
        "1 minute"
      );
    });

    // Select "Custom…"
    const selectTrigger = screen.getByTestId("interval-preset-select");
    await selectOption(selectTrigger, "Custom…");

    // Custom row should now be visible
    const amountInput = screen.getByTestId("custom-interval-amount");
    expect(amountInput).toBeInTheDocument();
    expect(amountInput).toHaveValue("1");

    const unitTrigger = screen.getByTestId("custom-interval-unit");
    expect(unitTrigger).toHaveTextContent("minutes");

    // Amendment 3: Nothing is dirty until the user edits!
    expect(screen.getByTestId("save-settings-button")).toBeDisabled();
  });

  it("editing custom input enables Save button and saves new value", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 60,
    });
    const updateSpy = vi
      .spyOn(api, "updateSettings")
      .mockResolvedValue({ check_interval_seconds: 300 });

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByTestId("interval-preset-select")).toBeInTheDocument();
    });

    // Switch to Custom…
    await selectOption(screen.getByTestId("interval-preset-select"), "Custom…");

    const amountInput = screen.getByTestId("custom-interval-amount");
    fireEvent.change(amountInput, { target: { value: "5" } });

    // Now dirty and valid -> Save is enabled
    const saveButton = screen.getByTestId("save-settings-button");
    expect(saveButton).toBeEnabled();

    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({ check_interval_seconds: 300 });
    });

    await waitFor(() => {
      expect(screen.getByTestId("saved-notice")).toHaveTextContent("Saved.");
      expect(screen.getByTestId("settings-live-region")).toHaveTextContent(
        "Settings saved."
      );
    });

    // Save should now be disabled again
    expect(screen.getByTestId("save-settings-button")).toBeDisabled();
  });

  it("displays validation error on invalid custom interval and disables Save", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 60,
    });

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByTestId("interval-preset-select")).toBeInTheDocument();
    });

    await selectOption(screen.getByTestId("interval-preset-select"), "Custom…");

    const amountInput = screen.getByTestId("custom-interval-amount");

    // Test 1: Empty input
    fireEvent.change(amountInput, { target: { value: "" } });
    expect(screen.getByTestId("custom-interval-error")).toHaveTextContent(
      "Enter an interval amount."
    );
    expect(amountInput).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByTestId("save-settings-button")).toBeDisabled();

    // Test 2: Non-digit input
    fireEvent.change(amountInput, { target: { value: "abc" } });
    expect(screen.getByTestId("custom-interval-error")).toHaveTextContent(
      "Enter a whole number of minutes."
    );
    expect(screen.getByTestId("save-settings-button")).toBeDisabled();

    // Test 3: Less than 10 seconds
    // Switch unit to seconds first
    await selectOption(screen.getByTestId("custom-interval-unit"), "seconds");
    fireEvent.change(amountInput, { target: { value: "5" } });

    expect(screen.getByTestId("custom-interval-error")).toHaveTextContent(
      "Choose an interval between 10 seconds and 365 days."
    );
    expect(screen.getByTestId("save-settings-button")).toBeDisabled();
  });

  it("handles save error: displays alert, keeps unsaved value, and re-enables Save (Amendment 4)", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 60,
    });
    vi.spyOn(api, "updateSettings").mockRejectedValue(
      new Error("Network failed")
    );

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByTestId("interval-preset-select")).toBeInTheDocument();
    });

    // Change to preset 30 seconds
    await selectOption(
      screen.getByTestId("interval-preset-select"),
      "30 seconds"
    );

    const saveButton = screen.getByTestId("save-settings-button");
    expect(saveButton).toBeEnabled();

    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByTestId("save-error-message")).toHaveTextContent(
        "Couldn't save settings. Try again."
      );
    });

    // Save button re-enabled so user can try again
    expect(saveButton).toBeEnabled();
    // Value is still the unsaved 30 seconds
    expect(screen.getByTestId("interval-preset-select")).toHaveTextContent(
      "30 seconds"
    );
  });

  it("handles load error and allows retry", async () => {
    const getSpy = vi
      .spyOn(api, "getSettings")
      .mockRejectedValueOnce(new Error("Server error"))
      .mockResolvedValueOnce({ check_interval_seconds: 60 });

    renderSettingsPage();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Couldn't load settings."
      );
    });

    const retryBtn = screen.getByTestId("retry-load-settings");
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByTestId("interval-preset-select")).toBeInTheDocument();
    });
    expect(getSpy).toHaveBeenCalledTimes(2);
  });

  it("changes theme immediately without Save button", async () => {
    vi.spyOn(api, "getSettings").mockResolvedValue({
      check_interval_seconds: 60,
    });

    renderSettingsPage();

    const themeSelect = screen.getByTestId("theme-select");
    expect(themeSelect).toHaveTextContent("Light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);

    await selectOption(themeSelect, "Dark");

    expect(themeSelect).toHaveTextContent("Dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(localStorage.getItem("camera-monitor-theme")).toBe("dark");

    // Appearance section has no save button
    expect(
      screen.getByText(
        "Applies immediately and is remembered on this computer."
      )
    ).toBeInTheDocument();
  });
});
