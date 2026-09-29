import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { StatusIndicator } from "@/components/StatusIndicator";

export function StyleguidePage() {
  const [isDark, setIsDark] = React.useState(() =>
    typeof document !== "undefined"
      ? document.documentElement.classList.contains("dark")
      : false
  );

  React.useEffect(() => {
    // Ensure dark class is cleaned up on unmount so it never leaks to other routes
    return () => {
      document.documentElement.classList.remove("dark");
    };
  }, []);

  const toggleDarkMode = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  return (
    <div
      data-testid="styleguide-page"
      className="space-y-10 py-4 font-sans text-foreground"
    >
      {/* Dev Unique Sentinel for Tree-Shaking Verification */}
      <div className="sr-only">__STYLEGUIDE_DEV_ONLY_UNIQUE_SENTINEL__</div>

      {/* Header & Local Dark Mode Toggle */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-page-title text-foreground">Design Styleguide</h1>
          <p className="text-sm text-muted-foreground">
            Development-only token reference, typography, spacing, and component
            verification.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={toggleDarkMode}
          data-testid="theme-toggle-button"
        >
          {isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
        </Button>
      </div>

      {/* 1. Typography Scale */}
      <section className="space-y-4" data-testid="section-typography">
        <h2 className="text-section-heading text-foreground">
          1. Typography Scale
        </h2>
        <div className="space-y-3 rounded-control border border-border bg-background p-4">
          <div>
            <span className="text-xs text-muted-foreground block mb-1">
              Page Title: 20px / 28px, Semibold (600) — utility: text-page-title
            </span>
            <div data-testid="sample-page-title" className="text-page-title">
              Camera Monitor Dashboard
            </div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block mb-1">
              Section Heading: 16px / 24px, Semibold (600) — utility:
              text-section-heading
            </span>
            <div
              data-testid="sample-section-heading"
              className="text-section-heading"
            >
              Monitoring Configuration & Outage Thresholds
            </div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block mb-1">
              Body Text: 14px / 20px, Regular (400) — utility: text-sm
            </span>
            <p data-testid="sample-body" className="text-sm">
              The monitoring engine performs ICMP reachability checks across all
              registered cameras concurrently.
            </p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block mb-1">
              Table Text: 13px / 18px, Tabular Figures — utility: text-table
            </span>
            <div data-testid="sample-table-text" className="text-table">
              192.0.2.10 — 28 online / 2 offline — Check cycle duration: 0.12s
            </div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block mb-1">
              Small / Helper Text: 12px / 16px, Regular (400) — utility: text-xs
            </span>
            <div
              data-testid="sample-small"
              className="text-xs text-muted-foreground"
            >
              Last check completed at 09:42:01. Failure streak: 0.
            </div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block mb-1">
              Tabular Numerals: Tabular Figures (tabular-nums)
            </span>
            <div
              data-testid="sample-tabular-nums"
              className="text-sm tabular-nums"
            >
              IP: 192.0.2.100 | Port: 8000 | Latency: 1.45ms | Timestamp:
              14:05:09
            </div>
          </div>
        </div>
      </section>

      {/* 2. Spacing & Container Grid */}
      <section className="space-y-4" data-testid="section-spacing">
        <h2 className="text-section-heading text-foreground">
          2. Spacing & Container Grid
        </h2>
        <div className="space-y-2 rounded-control border border-border bg-background p-4">
          <p className="text-sm text-muted-foreground">
            Base grid scale: 4px units. Page container max-width: 1200px
            (max-w-page).
          </p>
          <div
            data-testid="sample-page-container"
            className="max-w-page border border-border p-4 bg-muted/30 rounded-control"
          >
            <span className="text-xs text-muted-foreground">
              Container max-width: 1200px (`max-w-page`)
            </span>
          </div>
        </div>
      </section>

      {/* 3. StatusIndicator Component */}
      <section className="space-y-4" data-testid="section-status">
        <h2 className="text-section-heading text-foreground">
          3. Status Indicator (3 States)
        </h2>
        <div className="flex flex-wrap items-center gap-6 rounded-control border border-border bg-background p-4">
          <StatusIndicator status="online" data-testid="status-online" />
          <StatusIndicator status="offline" data-testid="status-offline" />
          <StatusIndicator status="unknown" data-testid="status-unknown" />
        </div>
      </section>

      {/* 4. Primitives */}
      <section className="space-y-6" data-testid="section-primitives">
        <h2 className="text-section-heading text-foreground">4. Primitives</h2>

        {/* Buttons */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Buttons (32px default, 28px small, 6px radius)
          </span>
          <div className="flex flex-wrap items-center gap-3 rounded-control border border-border bg-background p-4">
            <Button
              data-testid="button-default"
              variant="default"
              size="default"
            >
              Default Button
            </Button>
            <Button data-testid="button-sm" variant="default" size="sm">
              Small Button
            </Button>
            <Button
              data-testid="button-outline"
              variant="outline"
              size="default"
            >
              Outline
            </Button>
            <Button variant="secondary" size="default">
              Secondary
            </Button>
            <Button variant="ghost" size="default">
              Ghost
            </Button>
            <Button variant="destructive" size="default">
              Destructive
            </Button>
          </div>
        </div>

        {/* Form Controls: Input & Label */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Input & Label (32px height, 6px radius)
          </span>
          <div className="grid max-w-sm gap-2 rounded-control border border-border bg-background p-4">
            <Label htmlFor="demo-input">Camera IP Address</Label>
            <Input
              id="demo-input"
              data-testid="input-default"
              placeholder="192.0.2.10"
              defaultValue="192.0.2.10"
            />
          </div>
        </div>

        {/* Select */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Select (32px default, 28px small)
          </span>
          <div className="flex flex-wrap items-center gap-4 rounded-control border border-border bg-background p-4">
            <div className="w-48">
              <Select defaultValue="60">
                <SelectTrigger data-testid="select-default">
                  <SelectValue placeholder="Check interval" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">Every 30 seconds</SelectItem>
                  <SelectItem value="60">Every 60 seconds</SelectItem>
                  <SelectItem value="120">Every 2 minutes</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-40">
              <Select defaultValue="all">
                <SelectTrigger size="sm" data-testid="select-sm">
                  <SelectValue placeholder="Filter status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="online">Online only</SelectItem>
                  <SelectItem value="offline">Offline only</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Badges */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Badges (Compact, 6px radius, neutral)
          </span>
          <div className="flex flex-wrap items-center gap-2 rounded-control border border-border bg-background p-4">
            <Badge data-testid="badge-default" variant="default">
              Primary
            </Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="outline">Outline</Badge>
            <Badge variant="destructive">Destructive</Badge>
          </div>
        </div>

        {/* Table */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Table (13px/18px text-table, tabular-nums)
          </span>
          <div className="rounded-control border border-border bg-background">
            <Table data-testid="table-demo">
              <TableHeader>
                <TableRow>
                  <TableHead>Camera Name</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell data-testid="table-cell-name">
                    Front Entrance Cam
                  </TableCell>
                  <TableCell>Main Gate</TableCell>
                  <TableCell>192.0.2.10</TableCell>
                  <TableCell>
                    <StatusIndicator status="online" />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Loading Dock North</TableCell>
                  <TableCell>Warehouse</TableCell>
                  <TableCell>192.0.2.11</TableCell>
                  <TableCell>
                    <StatusIndicator status="offline" />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Dialog */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Dialog (8px rounded-dialog, bg-overlay)
          </span>
          <div className="rounded-control border border-border bg-background p-4">
            <Dialog>
              <DialogTrigger
                render={
                  <Button data-testid="dialog-trigger-button" variant="outline">
                    Open Test Dialog
                  </Button>
                }
              />
              <DialogContent data-testid="dialog-content-box">
                <DialogHeader>
                  <DialogTitle data-testid="dialog-title-box">
                    Confirm Action
                  </DialogTitle>
                  <DialogDescription>
                    This is a verification modal rendered with project tokens.
                  </DialogDescription>
                </DialogHeader>
                <p className="text-sm text-foreground">
                  Dialog content conforms to the 8px radius token and zero
                  elevation specifications.
                </p>
                <DialogFooter showCloseButton>
                  <Button variant="default" size="default">
                    Save Changes
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </section>
    </div>
  );
}

export default StyleguidePage;
