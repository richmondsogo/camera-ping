import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
            <Button
              data-testid="button-secondary"
              variant="secondary"
              size="default"
            >
              Secondary
            </Button>
            <Button data-testid="button-ghost" variant="ghost" size="default">
              Ghost
            </Button>
            <Button
              data-testid="button-destructive"
              variant="destructive"
              size="default"
            >
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
            <Input
              id="demo-placeholder-input"
              data-testid="input-placeholder"
              placeholder="192.0.2.20"
            />
          </div>
        </div>

        {/* Form Controls: Textarea & Label */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Textarea & Label (min-h-20, resize-none, 6px radius)
          </span>
          <div className="grid max-w-sm gap-2 rounded-control border border-border bg-background p-4">
            <Label htmlFor="demo-textarea">Description</Label>
            <Textarea
              id="demo-textarea"
              data-testid="textarea-default"
              defaultValue="Primary pan-tilt-zoom optical camera"
            />
            <Textarea
              id="demo-placeholder-textarea"
              data-testid="textarea-placeholder"
              placeholder="Enter optional notes..."
            />
          </div>
        </div>

        {/* Form States */}
        <div className="space-y-2" data-testid="section-form-states">
          <span className="text-xs text-muted-foreground block font-medium">
            Form States (aria-invalid border-error, error text)
          </span>
          <div className="grid max-w-sm gap-4 rounded-control border border-border bg-background p-4">
            <div className="space-y-1">
              <Label htmlFor="input-error">Input with error</Label>
              <Input
                id="input-error"
                data-testid="input-error"
                aria-invalid="true"
                defaultValue=""
                placeholder="Camera name"
              />
              <p data-testid="form-error-text" className="text-xs text-error">
                This field cannot be empty.
              </p>
            </div>
            <div className="space-y-1">
              <Label htmlFor="textarea-normal">Textarea normal</Label>
              <Textarea
                id="textarea-normal"
                data-testid="textarea-normal"
                defaultValue="Normal textarea notes"
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="textarea-error">Textarea with error</Label>
              <Textarea
                id="textarea-error"
                data-testid="textarea-error"
                aria-invalid="true"
                defaultValue="Invalid long text"
              />
              <p className="text-xs text-error">
                Description cannot exceed 500 characters.
              </p>
            </div>
            <div className="space-y-1">
              <Label htmlFor="select-error">Select with error</Label>
              <Select>
                <SelectTrigger
                  id="select-error"
                  data-testid="select-error"
                  aria-invalid="true"
                >
                  <SelectValue placeholder="Select location" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gate">Main Gate</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-error">Please select a location.</p>
            </div>
          </div>
        </div>

        {/* Select */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Select (32px default, 28px small)
          </span>
          <div className="flex flex-wrap items-center gap-inline rounded-control border border-border bg-background p-4">
            <div className="w-52">
              <Select defaultValue="60">
                <SelectTrigger data-testid="select-default">
                  <SelectValue placeholder="Check interval" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 seconds</SelectItem>
                  <SelectItem value="60">1 minute</SelectItem>
                  <SelectItem value="120">2 minutes</SelectItem>
                  <SelectItem value="300">5 minutes</SelectItem>
                  <SelectItem value="600">10 minutes</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="w-44">
              <Select defaultValue="all">
                <SelectTrigger size="sm" data-testid="select-sm">
                  <SelectValue placeholder="Filter status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="online">Online only</SelectItem>
                  <SelectItem value="offline">Offline only</SelectItem>
                  <SelectItem value="unknown">Unknown only</SelectItem>
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
          <div className="flex flex-wrap items-center gap-tight rounded-control border border-border bg-background p-4">
            <Badge data-testid="badge-default" variant="default">
              Primary
            </Badge>
            <Badge data-testid="badge-secondary" variant="secondary">
              Secondary
            </Badge>
            <Badge data-testid="badge-outline" variant="outline">
              Outline
            </Badge>
            <Badge data-testid="badge-destructive" variant="destructive">
              Destructive
            </Badge>
          </div>
        </div>

        {/* Table */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Table (13px/18px text-table, fixed layout, 6-row contract)
          </span>
          <div className="rounded-control border border-border bg-background">
            <Table data-testid="table-demo">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-2/12" data-testid="table-head-name">
                    Camera Name
                  </TableHead>
                  <TableHead className="w-2/12">Location</TableHead>
                  <TableHead
                    className="w-4/12"
                    data-testid="table-head-description"
                  >
                    Description
                  </TableHead>
                  <TableHead className="w-2/12">IP Address</TableHead>
                  <TableHead className="w-1/12">Status</TableHead>
                  <TableHead className="w-1/12">Last Checked</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow data-testid="table-row-sample">
                  <TableCell data-testid="table-cell-name">
                    Front Entrance Cam
                  </TableCell>
                  <TableCell>Main Gate</TableCell>
                  <TableCell>
                    <div
                      className="truncate"
                      title="Primary pan-tilt-zoom optical camera covering south perimeter entry and truck weighbridge"
                      data-testid="table-cell-description"
                    >
                      Primary pan-tilt-zoom optical camera covering south
                      perimeter entry and truck weighbridge
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">192.0.2.10</TableCell>
                  <TableCell>
                    <StatusIndicator status="online" />
                  </TableCell>
                  <TableCell className="tabular-nums">10:42:01</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Visitor Parking North</TableCell>
                  <TableCell>Main Gate</TableCell>
                  <TableCell>
                    <div className="truncate" title="Fixed dome camera">
                      Fixed dome camera
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">192.0.2.11</TableCell>
                  <TableCell>
                    <StatusIndicator status="online" />
                  </TableCell>
                  <TableCell className="tabular-nums">10:42:01</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Staff Turnstile East</TableCell>
                  <TableCell>Main Gate</TableCell>
                  <TableCell>
                    <div className="truncate" title="Pedestrian access gate">
                      Pedestrian access gate
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">192.0.2.12</TableCell>
                  <TableCell>
                    <StatusIndicator status="online" />
                  </TableCell>
                  <TableCell className="tabular-nums">10:42:00</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Loading Dock Bay 1</TableCell>
                  <TableCell>Warehouse</TableCell>
                  <TableCell>
                    <div className="truncate" title="Overhead bay view">
                      Overhead bay view
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">192.0.2.13</TableCell>
                  <TableCell>
                    <StatusIndicator status="offline" />
                  </TableCell>
                  <TableCell className="tabular-nums">10:41:45</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Server Room Rack A</TableCell>
                  <TableCell>Data Center</TableCell>
                  <TableCell>
                    <div
                      className="truncate"
                      title="Interior environmental view"
                    >
                      Interior environmental view
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">192.0.2.14</TableCell>
                  <TableCell>
                    <StatusIndicator status="online" />
                  </TableCell>
                  <TableCell className="tabular-nums">10:42:02</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Perimeter Fence West</TableCell>
                  <TableCell>Backlot</TableCell>
                  <TableCell>
                    <div className="truncate" title="Infrared boundary sensor">
                      Infrared boundary sensor
                    </div>
                  </TableCell>
                  <TableCell className="tabular-nums">192.0.2.15</TableCell>
                  <TableCell>
                    <StatusIndicator status="unknown" />
                  </TableCell>
                  <TableCell className="tabular-nums">Never</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Dialog */}
        <div className="space-y-2">
          <span className="text-xs text-muted-foreground block font-medium">
            Dialog (8px rounded-dialog, bg-overlay, 480px width)
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
                  <DialogDescription data-testid="dialog-description-box">
                    This is a verification modal rendered with project tokens.
                  </DialogDescription>
                </DialogHeader>
                <p className="text-sm text-foreground">
                  Dialog content conforms to the 8px radius token, 24px padding,
                  and zero elevation specifications.
                </p>
                <p
                  data-testid="dialog-error-text"
                  className="text-xs text-error"
                >
                  An error occurred in this dialog.
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

      {/* 5. Layout Specimens (Previews to be replaced by real screens) */}
      <section className="space-y-6" data-testid="section-layout-specimens">
        <h2 className="text-section-heading text-foreground">
          5. Layout Specimens (Design Previews)
        </h2>

        {/* Specimen 1: Page Composition */}
        <div className="rounded-control border border-border bg-background p-6 space-y-stack">
          <div className="border-b border-border pb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              Layout Specimen 1: Page Composition (To be replaced by real
              screen)
            </span>
          </div>

          <div>
            <h3 className="text-page-title text-foreground">Camera Monitor</h3>
          </div>

          <div className="space-y-toolbar">
            {/* Toolbar */}
            <div className="flex flex-wrap items-center justify-between gap-inline">
              <div className="flex flex-wrap items-center gap-inline">
                <Input
                  placeholder="Search cameras..."
                  className="w-64"
                  data-testid="specimen-search-input"
                />
                <div className="w-40">
                  <Select defaultValue="all">
                    <SelectTrigger size="default">
                      <SelectValue placeholder="All Statuses" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Statuses</SelectItem>
                      <SelectItem value="online">Online</SelectItem>
                      <SelectItem value="offline">Offline</SelectItem>
                      <SelectItem value="unknown">Unknown</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="w-44">
                  <Select defaultValue="all">
                    <SelectTrigger size="default">
                      <SelectValue placeholder="All Locations" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Locations</SelectItem>
                      <SelectItem value="main-gate">Main Gate</SelectItem>
                      <SelectItem value="warehouse">Warehouse</SelectItem>
                      <SelectItem value="data-center">Data Center</SelectItem>
                      <SelectItem value="backlot">Backlot</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex items-center gap-tight">
                <Button variant="outline">Export CSV</Button>
                <Button variant="default">Add Camera</Button>
              </div>
            </div>

            {/* Table */}
            <div className="rounded-control border border-border bg-background">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-2/12">Camera Name</TableHead>
                    <TableHead className="w-2/12">Location</TableHead>
                    <TableHead className="w-4/12">Description</TableHead>
                    <TableHead className="w-2/12">IP Address</TableHead>
                    <TableHead className="w-1/12">Status</TableHead>
                    <TableHead className="w-1/12">Last Checked</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow>
                    <TableCell>Front Entrance Cam</TableCell>
                    <TableCell>Main Gate</TableCell>
                    <TableCell>
                      <div
                        className="truncate"
                        title="Primary pan-tilt-zoom optical camera covering south perimeter entry and truck weighbridge"
                      >
                        Primary pan-tilt-zoom optical camera covering south
                        perimeter entry and truck weighbridge
                      </div>
                    </TableCell>
                    <TableCell className="tabular-nums">192.0.2.10</TableCell>
                    <TableCell>
                      <StatusIndicator status="online" />
                    </TableCell>
                    <TableCell className="tabular-nums">10:42:01</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Visitor Parking North</TableCell>
                    <TableCell>Main Gate</TableCell>
                    <TableCell>
                      <div className="truncate" title="Fixed dome camera">
                        Fixed dome camera
                      </div>
                    </TableCell>
                    <TableCell className="tabular-nums">192.0.2.11</TableCell>
                    <TableCell>
                      <StatusIndicator status="online" />
                    </TableCell>
                    <TableCell className="tabular-nums">10:42:01</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Staff Turnstile East</TableCell>
                    <TableCell>Main Gate</TableCell>
                    <TableCell>
                      <div className="truncate" title="Pedestrian access gate">
                        Pedestrian access gate
                      </div>
                    </TableCell>
                    <TableCell className="tabular-nums">192.0.2.12</TableCell>
                    <TableCell>
                      <StatusIndicator status="online" />
                    </TableCell>
                    <TableCell className="tabular-nums">10:42:00</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </div>
        </div>

        {/* Specimen 2: Settings Form */}
        <div className="rounded-control border border-border bg-background p-6 space-y-stack">
          <div className="border-b border-border pb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block">
              Layout Specimen 2: Settings Form (To be replaced by real screen)
            </span>
          </div>

          <form
            className="max-w-md space-y-stack"
            onSubmit={(e) => e.preventDefault()}
          >
            {/* Field 1 */}
            <div className="space-y-tight">
              <Label htmlFor="specimen-ip-range">Camera Subnet CIDR</Label>
              <Input
                id="specimen-ip-range"
                defaultValue="192.0.2.0/24"
                placeholder="192.0.2.0/24"
              />
              <p className="text-xs text-muted-foreground">
                RFC 5737 subnet used for camera discovery scan.
              </p>
            </div>

            {/* Field 2 */}
            <div className="space-y-tight">
              <Label htmlFor="specimen-interval">Check Interval</Label>
              <Select defaultValue="60">
                <SelectTrigger id="specimen-interval">
                  <SelectValue placeholder="Select interval" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">30 seconds</SelectItem>
                  <SelectItem value="60">1 minute</SelectItem>
                  <SelectItem value="120">2 minutes</SelectItem>
                  <SelectItem value="300">5 minutes</SelectItem>
                  <SelectItem value="600">10 minutes</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Frequency of ICMP reachability checks.
              </p>
            </div>

            {/* Field 3 */}
            <div className="space-y-tight">
              <Label htmlFor="specimen-email">Alert Email Recipient</Label>
              <Input
                id="specimen-email"
                type="email"
                placeholder="admin@local.office"
                defaultValue="admin@local.office"
              />
              <p className="text-xs text-muted-foreground">
                Receives alert email upon reaching 10 consecutive check
                failures.
              </p>
            </div>

            <Button type="submit" variant="default">
              Save Changes
            </Button>
          </form>
        </div>
      </section>
    </div>
  );
}

export default StyleguidePage;
