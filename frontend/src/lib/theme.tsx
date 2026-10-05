/* eslint-disable react-refresh/only-export-components */
import * as React from "react";

export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "camera-monitor-theme";

export function readStoredTheme(): Theme {
  try {
    if (typeof window === "undefined" || !window.localStorage) {
      return "light";
    }
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "dark" || stored === "light") {
      return stored;
    }
    return "light";
  } catch {
    return "light";
  }
}

export function writeStoredTheme(theme: Theme): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme);
    }
  } catch {
    // Intentionally suppressed: storage write must never throw
  }
}

export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") {
    return;
  }
  if (theme === "dark") {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

export function ThemeProvider({
  children,
  initialTheme,
}: {
  children: React.ReactNode;
  initialTheme?: Theme;
}) {
  const [theme, setThemeState] = React.useState<Theme>(
    () => initialTheme ?? readStoredTheme()
  );

  const prevThemeRef = React.useRef<Theme | undefined>(undefined);

  // Apply .dark class ONLY on mount and when theme value actually changes.
  // Never re-apply on unrelated re-renders to prevent undoing external tests (e.g. contrast.spec.ts).
  React.useEffect(() => {
    if (prevThemeRef.current !== theme) {
      applyTheme(theme);
      prevThemeRef.current = theme;
    }
  }, [theme]);

  const setTheme = React.useCallback((nextTheme: Theme) => {
    setThemeState(nextTheme);
    writeStoredTheme(nextTheme);
  }, []);

  const toggleTheme = React.useCallback(() => {
    setThemeState((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      writeStoredTheme(next);
      return next;
    });
  }, []);

  const value = React.useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = React.useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
