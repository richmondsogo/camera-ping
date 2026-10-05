import { act, render, renderHook } from "@testing-library/react";
import * as React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  ThemeProvider,
  applyTheme,
  readStoredTheme,
  useTheme,
  writeStoredTheme,
} from "./theme";

describe("theme module", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  describe("readStoredTheme / writeStoredTheme", () => {
    it("reads default 'light' when nothing is in storage", () => {
      expect(readStoredTheme()).toBe("light");
    });

    it("reads 'dark' or 'light' correctly", () => {
      localStorage.setItem("camera-monitor-theme", "dark");
      expect(readStoredTheme()).toBe("dark");

      localStorage.setItem("camera-monitor-theme", "light");
      expect(readStoredTheme()).toBe("light");
    });

    it("falls back to 'light' for invalid values in storage", () => {
      localStorage.setItem("camera-monitor-theme", "invalid-value");
      expect(readStoredTheme()).toBe("light");
    });

    it("writes theme to storage", () => {
      writeStoredTheme("dark");
      expect(localStorage.getItem("camera-monitor-theme")).toBe("dark");

      writeStoredTheme("light");
      expect(localStorage.getItem("camera-monitor-theme")).toBe("light");
    });
  });

  describe("applyTheme", () => {
    it("adds or removes dark class on document.documentElement", () => {
      applyTheme("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);

      applyTheme("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
  });

  describe("ThemeProvider and useTheme", () => {
    it("throws error if useTheme is called outside ThemeProvider", () => {
      expect(() => {
        renderHook(() => useTheme());
      }).toThrow("useTheme must be used within a ThemeProvider");
    });

    it("provides initial theme and responds to toggleTheme", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe("dark");
      expect(localStorage.getItem("camera-monitor-theme")).toBe("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe("light");
      expect(localStorage.getItem("camera-monitor-theme")).toBe("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });

    it("allows explicitly setting theme with setTheme", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme("dark");
      });

      expect(result.current.theme).toBe("dark");
      expect(localStorage.getItem("camera-monitor-theme")).toBe("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);

      act(() => {
        result.current.setTheme("light");
      });

      expect(result.current.theme).toBe("light");
      expect(localStorage.getItem("camera-monitor-theme")).toBe("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });

    it("initializes from stored dark theme", () => {
      localStorage.setItem("camera-monitor-theme", "dark");

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ThemeProvider>{children}</ThemeProvider>
      );

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe("dark");
      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("renders children correctly", () => {
      const { getByText } = render(
        <ThemeProvider>
          <div>Test Content</div>
        </ThemeProvider>
      );

      expect(getByText("Test Content")).toBeInTheDocument();
    });
  });
});
