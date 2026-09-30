import { NavLink, Outlet } from "react-router";
import { cn } from "@/lib/utils";

export function AppShell() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <header className="h-header border-b border-border bg-background box-border">
        <div className="max-w-page mx-auto px-gutter h-full flex items-center justify-between">
          <div className="flex items-center gap-stack">
            <span className="text-sm font-semibold tracking-tight text-foreground">
              Camera Monitor
            </span>
            <nav aria-label="Main" className="flex items-center gap-1 h-full">
              <NavLink
                to="/"
                end
                data-testid="nav-dashboard"
                className={({ isActive }) =>
                  cn(
                    "inline-flex items-center h-full px-control-x border-b-2 text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    isActive
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Dashboard
              </NavLink>
              <NavLink
                to="/settings"
                data-testid="nav-settings"
                className={({ isActive }) =>
                  cn(
                    "inline-flex items-center h-full px-control-x border-b-2 text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    isActive
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )
                }
              >
                Settings
              </NavLink>
            </nav>
          </div>
        </div>
      </header>
      <main className="max-w-page w-full mx-auto px-gutter pt-section pb-container-bottom flex-1">
        <Outlet />
      </main>
    </div>
  );
}

export default AppShell;
