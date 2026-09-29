import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router";
import { AppShell } from "@/components/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { SettingsPage } from "@/pages/SettingsPage";

// Register /_design only when import.meta.env.DEV, via dynamic import so it is tree-shaken
const StyleguidePage = import.meta.env.DEV
  ? lazy(() => import("@/pages/StyleguidePage"))
  : null;

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="settings" element={<SettingsPage />} />
        {import.meta.env.DEV && StyleguidePage && (
          <Route
            path="_design"
            element={
              <Suspense fallback={null}>
                <StyleguidePage />
              </Suspense>
            }
          />
        )}
      </Route>
    </Routes>
  );
}

export default App;
