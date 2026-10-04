import * as React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ImportCamerasDialog } from "./ImportCamerasDialog";
import { api, ApiError } from "@/lib/api";

describe("ImportCamerasDialog", () => {
  const onSuccess = vi.fn();
  const onOpenChange = vi.fn();
  let importButtonRef: React.RefObject<HTMLButtonElement | null>;

  beforeEach(() => {
    vi.restoreAllMocks();
    onSuccess.mockReset();
    onOpenChange.mockReset();
    const btn = document.createElement("button");
    btn.textContent = "Import";
    document.body.appendChild(btn);
    importButtonRef = { current: btn };
  });

  it("renders dialog with file input, instructions, and template link", () => {
    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    expect(
      screen.getByRole("heading", { name: "Import Cameras" })
    ).toBeDefined();
    expect(screen.getByTestId("download-template-link")).toBeDefined();
    expect(screen.getByLabelText("Choose CSV file")).toBeDefined();
    expect(screen.getByTestId("import-cancel-button")).toBeDefined();
  });

  it("handles valid file for 1 camera with singular plurals", async () => {
    const importSpy = vi.spyOn(api, "importCameras").mockResolvedValue({
      count: 1,
      preview: [
        {
          camera_name: "Cam 1",
          location: "Lobby",
          description: "Front door",
          ip_address: "192.0.2.101",
        },
      ],
    });

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(
      [
        "camera_name,location,description,ip_address\nCam 1,Lobby,Front door,192.0.2.101",
      ],
      "cameras.csv",
      { type: "text/csv" }
    );

    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("1 camera will be added.")).toBeDefined();
    });

    expect(importSpy).toHaveBeenCalledWith(file, true);
    expect(
      screen.getByRole("button", { name: /Import 1 camera/i })
    ).toBeDefined();
  });

  it("handles valid file for multiple cameras with plural text and confirms import", async () => {
    const importSpy = vi.spyOn(api, "importCameras");
    importSpy.mockResolvedValueOnce({
      count: 2,
      preview: [
        {
          camera_name: "Cam 1",
          location: "Lobby",
          description: "Front",
          ip_address: "192.0.2.101",
        },
        {
          camera_name: "Cam 2",
          location: "Back",
          description: "Rear",
          ip_address: "192.0.2.102",
        },
      ],
    });
    importSpy.mockResolvedValueOnce({
      imported: 2,
    });

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(["dummy content"], "cameras.csv", {
      type: "text/csv",
    });
    const input = screen.getByTestId("csv-file-input");
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("2 cameras will be added.")).toBeDefined();
    });

    const confirmBtn = screen.getByRole("button", {
      name: /Import 2 cameras/i,
    });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(importSpy).toHaveBeenCalledWith(file, false);
      expect(onSuccess).toHaveBeenCalledWith(2);
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("displays validation error table and returns to file-choice on 'Choose another file'", async () => {
    vi.spyOn(api, "importCameras").mockRejectedValue(
      new ApiError({
        kind: "http",
        status: 422,
        message: "Unprocessable",
        detail: [
          {
            loc: ["file", 2, "ip_address"],
            msg: "Invalid IP address format.",
            type: "value_error",
          },
          {
            loc: ["file", 3, "camera_name"],
            msg: "Camera name cannot be empty.",
            type: "value_error",
          },
        ],
        totalErrors: 2,
      })
    );

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(["bad content"], "cameras.csv", { type: "text/csv" });
    fireEvent.change(screen.getByTestId("csv-file-input"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(
        screen.getByText("2 problems found. Nothing was imported.")
      ).toBeDefined();
    });

    expect(screen.getByText("Invalid IP address format.")).toBeDefined();
    expect(screen.getByText("Camera name cannot be empty.")).toBeDefined();
    expect(screen.queryByTestId("import-confirm-button")).toBeNull();

    // Click "Choose another file"
    fireEvent.click(screen.getByTestId("choose-another-file-button"));

    await waitFor(() => {
      expect(screen.getByLabelText("Choose CSV file")).toBeDefined();
    });
  });

  it("handles NotReadableError on file read (Amendment 3)", async () => {
    const notReadableError = new Error(
      "The requested file could not be read, typically due to permission problems that have occurred after a reference to a file was acquired."
    );
    notReadableError.name = "NotReadableError";

    vi.spyOn(api, "importCameras").mockRejectedValue(notReadableError);

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(["locked content"], "cameras.csv", {
      type: "text/csv",
    });
    fireEvent.change(screen.getByTestId("csv-file-input"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain(
        "Couldn't read the file. Close it in Excel and choose it again."
      );
    });

    // Should return to file-choice state
    expect(screen.getByLabelText("Choose CSV file")).toBeDefined();
  });

  it("handles NotReadableError during confirm step (Amendment 3)", async () => {
    const importSpy = vi.spyOn(api, "importCameras");
    importSpy.mockResolvedValueOnce({
      count: 1,
      preview: [
        {
          camera_name: "Cam 1",
          location: "Lobby",
          description: "Front",
          ip_address: "192.0.2.101",
        },
      ],
    });

    const notReadableError = new Error("File locked");
    notReadableError.name = "NotReadableError";
    importSpy.mockRejectedValueOnce(notReadableError);

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(["content"], "cameras.csv", { type: "text/csv" });
    fireEvent.change(screen.getByTestId("csv-file-input"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Import 1 camera/i })
      ).toBeDefined();
    });

    fireEvent.click(screen.getByRole("button", { name: /Import 1 camera/i }));

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain(
        "Couldn't read the file. Close it in Excel and choose it again."
      );
    });

    // Returned to file-choice state
    expect(screen.getByLabelText("Choose CSV file")).toBeDefined();
  });

  it("handles 413 file too large error", async () => {
    vi.spyOn(api, "importCameras").mockRejectedValue(
      new ApiError({
        kind: "http",
        status: 413,
        message: "Payload Too Large",
      })
    );

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(["huge content"], "cameras.csv", {
      type: "text/csv",
    });
    fireEvent.change(screen.getByTestId("csv-file-input"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(screen.getByText("File size exceeds 1 MiB limit.")).toBeDefined();
      expect(
        screen.getByText("1 problem found. Nothing was imported.")
      ).toBeDefined();
    });
  });

  it("handles 409 conflict error on confirm step", async () => {
    const importSpy = vi.spyOn(api, "importCameras");
    importSpy.mockResolvedValueOnce({
      count: 1,
      preview: [
        {
          camera_name: "Cam 1",
          location: "Lobby",
          description: "Front",
          ip_address: "192.0.2.101",
        },
      ],
    });
    importSpy.mockRejectedValueOnce(
      new ApiError({
        kind: "http",
        status: 409,
        message: "Conflict",
      })
    );

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(["content"], "cameras.csv", { type: "text/csv" });
    fireEvent.change(screen.getByTestId("csv-file-input"), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Import 1 camera/i })
      ).toBeDefined();
    });

    fireEvent.click(screen.getByRole("button", { name: /Import 1 camera/i }));

    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain(
        "Another camera with one of these IP addresses was added in the meantime. Nothing was imported. Try again."
      );
    });

    // Returned to file-choice state
    expect(screen.getByLabelText("Choose CSV file")).toBeDefined();
  });

  it("blocks Escape key dismissal while request is pending", async () => {
    let resolveImport: (val: unknown) => void = () => {};
    const pendingPromise = new Promise((resolve) => {
      resolveImport = resolve;
    });

    vi.spyOn(api, "importCameras").mockReturnValue(
      pendingPromise as ReturnType<typeof api.importCameras>
    );

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    const file = new File(["content"], "cameras.csv", { type: "text/csv" });
    fireEvent.change(screen.getByTestId("csv-file-input"), {
      target: { files: [file] },
    });

    // While validating
    expect(screen.getByText("Validating file...")).toBeDefined();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onOpenChange).not.toHaveBeenCalled();

    // Clean up pending promise and await UI update
    await React.act(async () => {
      resolveImport({
        count: 1,
        preview: [
          {
            camera_name: "Cam 1",
            location: "Lobby",
            description: "Front",
            ip_address: "192.0.2.101",
          },
        ],
      });
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /Import 1 camera/i })
      ).toBeDefined();
    });
  });

  it("restores focus to importButtonRef when Cancel is clicked", () => {
    const focusSpy = vi.spyOn(importButtonRef.current!, "focus");

    render(
      <ImportCamerasDialog
        open={true}
        onOpenChange={onOpenChange}
        onSuccess={onSuccess}
        importButtonRef={importButtonRef}
      />
    );

    fireEvent.click(screen.getByTestId("import-cancel-button"));
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(focusSpy).toHaveBeenCalled();
  });
});
