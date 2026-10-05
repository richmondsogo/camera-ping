import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
  INTERVAL_PRESETS,
  UNIT_SELECT_ITEMS,
  formatInterval,
  parseAmount,
  secondsToCustom,
  toSeconds,
  validateInterval,
  type TimeUnit,
} from "@/features/settings/utils";
import { api } from "@/lib/api";
import { useTheme } from "@/lib/theme";

const PRESET_VALUES = new Set(["10", "30", "60", "120", "300", "600"]);

const SELECT_ITEMS_PRESETS = [
  ...INTERVAL_PRESETS.map((p) => ({ value: p.value, label: p.label })),
  { value: "custom", label: "Custom…" },
];

const THEME_SELECT_ITEMS = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();

  // Settings query
  const {
    data: settings,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings(),
  });

  // Server value in seconds (default fallback 60 if not yet loaded)
  const serverSeconds = settings?.check_interval_seconds ?? 60;

  // Selected preset mode: "10" | "30" | "60" | "120" | "300" | "600" | "custom"
  const [selectMode, setSelectMode] = React.useState<string>("60");
  const [customAmount, setCustomAmount] = React.useState<string>("1");
  const [customUnit, setCustomUnit] = React.useState<TimeUnit>("minutes");
  const [isCustomEdited, setIsCustomEdited] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [savedNotice, setSavedNotice] = React.useState(false);
  const [liveAnnouncement, setLiveAnnouncement] = React.useState("");

  // Sync state when server data is loaded
  React.useEffect(() => {
    if (settings) {
      const sec = settings.check_interval_seconds;
      const str = String(sec);
      if (PRESET_VALUES.has(str)) {
        setSelectMode(str);
        const { amount, unit } = secondsToCustom(sec);
        setCustomAmount(String(amount));
        setCustomUnit(unit);
        setIsCustomEdited(false);
      } else {
        setSelectMode("custom");
        const { amount, unit } = secondsToCustom(sec);
        setCustomAmount(String(amount));
        setCustomUnit(unit);
        setIsCustomEdited(false);
      }
    }
  }, [settings]);

  // Notice timeout
  React.useEffect(() => {
    if (savedNotice) {
      const timer = setTimeout(() => {
        setSavedNotice(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [savedNotice]);

  // Calculate current effective interval and validity
  let effectiveSeconds: number | null = null;
  let validationError: string | null = null;

  if (selectMode !== "custom") {
    effectiveSeconds = Number.parseInt(selectMode, 10);
  } else {
    validationError = validateInterval(customAmount, customUnit);
    if (!validationError) {
      const parsed = parseAmount(customAmount);
      if (parsed !== null) {
        effectiveSeconds = toSeconds(parsed, customUnit);
      }
    }
  }

  // Calculate isDirty:
  // If in preset mode: dirty if selected preset !== String(serverSeconds)
  // If in custom mode:
  //   - If server was preset, and user selected custom: dirty ONLY if user edited or value != server
  //   - Per Amendment 3: Choosing "Custom…" prefills secondsToCustom(current value) and nothing is dirty until user edits.
  const isDirty = React.useMemo(() => {
    if (selectMode !== "custom") {
      return Number.parseInt(selectMode, 10) !== serverSeconds;
    }
    // Custom mode
    if (!isCustomEdited) {
      return false;
    }
    if (effectiveSeconds === null || validationError !== null) {
      return false;
    }
    return effectiveSeconds !== serverSeconds;
  }, [
    selectMode,
    serverSeconds,
    isCustomEdited,
    effectiveSeconds,
    validationError,
  ]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (seconds: number) =>
      api.updateSettings({ check_interval_seconds: seconds }),
    onSuccess: (data) => {
      queryClient.setQueryData(["settings"], data);
      void queryClient.invalidateQueries({
        queryKey: ["monitoring", "status"],
      });
      setSaveError(null);
      setSavedNotice(true);
      setLiveAnnouncement("Settings saved.");
      setIsCustomEdited(false);
    },
    onError: () => {
      setSaveError("Couldn't save settings. Try again.");
    },
  });

  const handleSelectModeChange = (val: string | null) => {
    if (!val) return;
    setSelectMode(val);
    setSaveError(null);
    if (val === "custom") {
      // Prefill from current effective value or server value
      const baseSeconds =
        selectMode !== "custom"
          ? Number.parseInt(selectMode, 10)
          : serverSeconds;
      const { amount, unit } = secondsToCustom(baseSeconds);
      setCustomAmount(String(amount));
      setCustomUnit(unit);
      setIsCustomEdited(false); // Amendment 3: clean until user edits
    }
  };

  const handleCustomAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCustomAmount(e.target.value);
    setIsCustomEdited(true);
    setSaveError(null);
  };

  const handleCustomUnitChange = (unit: TimeUnit | null) => {
    if (!unit) return;
    setCustomUnit(unit);
    setIsCustomEdited(true);
    setSaveError(null);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isDirty || effectiveSeconds === null || validationError !== null) {
      return;
    }
    setSaveError(null);
    saveMutation.mutate(effectiveSeconds);
  };

  return (
    <div
      data-testid="settings-page"
      className="max-w-page space-y-stack py-4 font-sans text-foreground"
    >
      {/* Screen Reader Live Region */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="settings-live-region"
      >
        {liveAnnouncement}
      </div>

      <div>
        <h1 className="text-page-title text-foreground">Settings</h1>
      </div>

      {/* Monitoring Section */}
      <section
        aria-labelledby="monitoring-settings-heading"
        className="space-y-4 rounded-control border border-border bg-background p-panel-pad"
        data-testid="monitoring-settings-section"
      >
        <h2
          id="monitoring-settings-heading"
          className="text-section-heading text-foreground"
        >
          Monitoring
        </h2>

        {isLoading ? (
          <div className="text-sm text-muted-foreground">Loading settings…</div>
        ) : isError ? (
          <div className="space-y-2">
            <p role="alert" className="text-sm text-error">
              Couldn't load settings.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void refetch()}
              data-testid="retry-load-settings"
            >
              Retry
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSave} className="max-w-md space-y-4">
            {/* Check Interval Preset Select */}
            <div className="space-y-tight">
              <Label htmlFor="interval-preset-select">Check Interval</Label>
              <div className="w-56">
                <Select
                  items={SELECT_ITEMS_PRESETS}
                  value={selectMode}
                  onValueChange={handleSelectModeChange}
                >
                  <SelectTrigger
                    id="interval-preset-select"
                    data-testid="interval-preset-select"
                  >
                    <SelectValue placeholder="Select check interval" />
                  </SelectTrigger>
                  <SelectContent>
                    {SELECT_ITEMS_PRESETS.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Custom Interval Row */}
            {selectMode === "custom" && (
              <div
                className="space-y-tight"
                data-testid="custom-interval-container"
              >
                <Label htmlFor="custom-interval-amount">Custom Interval</Label>
                <div className="flex items-center gap-inline">
                  <div className="w-28">
                    <Input
                      id="custom-interval-amount"
                      type="text"
                      inputMode="numeric"
                      maxLength={9}
                      value={customAmount}
                      onChange={handleCustomAmountChange}
                      aria-label="Interval amount"
                      aria-invalid={validationError !== null}
                      aria-describedby={
                        validationError ? "custom-interval-error" : undefined
                      }
                      data-testid="custom-interval-amount"
                      className="h-control"
                    />
                  </div>
                  <div className="w-44">
                    <Select
                      items={UNIT_SELECT_ITEMS}
                      value={customUnit}
                      onValueChange={handleCustomUnitChange}
                    >
                      <SelectTrigger
                        aria-label="Interval unit"
                        data-testid="custom-interval-unit"
                      >
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {UNIT_SELECT_ITEMS.map((item) => (
                          <SelectItem key={item.value} value={item.value}>
                            {item.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {validationError && (
                  <p
                    id="custom-interval-error"
                    role="alert"
                    className="text-xs text-error"
                    data-testid="custom-interval-error"
                  >
                    {validationError}
                  </p>
                )}
              </div>
            )}

            {/* Helper text or Long interval warning */}
            {effectiveSeconds !== null && effectiveSeconds >= 3600 ? (
              <p
                className="text-xs font-medium text-amber-700 dark:text-amber-400"
                data-testid="long-interval-warning"
              >
                Outages may take up to {formatInterval(effectiveSeconds)} to
                detect.
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">
                How often camera reachability is tested.
              </p>
            )}

            {/* Save error banner */}
            {saveError && (
              <p
                role="alert"
                className="text-xs text-error"
                data-testid="save-error-message"
              >
                {saveError}
              </p>
            )}

            {/* Actions: Save button & Saved notice */}
            <div className="flex items-center gap-tight pt-2">
              <Button
                type="submit"
                variant="default"
                disabled={
                  !isDirty || saveMutation.isPending || validationError !== null
                }
                data-testid="save-settings-button"
              >
                {saveMutation.isPending ? "Saving…" : "Save"}
              </Button>

              {savedNotice && (
                <span
                  className="text-xs font-medium text-status-online"
                  data-testid="saved-notice"
                >
                  Saved.
                </span>
              )}
            </div>
          </form>
        )}
      </section>

      {/* Appearance Section */}
      <section
        aria-labelledby="appearance-settings-heading"
        className="space-y-4 rounded-control border border-border bg-background p-panel-pad"
        data-testid="appearance-settings-section"
      >
        <h2
          id="appearance-settings-heading"
          className="text-section-heading text-foreground"
        >
          Appearance
        </h2>

        <div className="max-w-md space-y-tight">
          <Label htmlFor="theme-select">Theme</Label>
          <div className="w-56">
            <Select
              items={THEME_SELECT_ITEMS}
              value={theme}
              onValueChange={(val) => {
                if (val === "light" || val === "dark") setTheme(val);
              }}
            >
              <SelectTrigger id="theme-select" data-testid="theme-select">
                <SelectValue placeholder="Select theme" />
              </SelectTrigger>
              <SelectContent>
                {THEME_SELECT_ITEMS.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <p className="text-xs text-muted-foreground">
            Applies immediately and is remembered on this computer.
          </p>
        </div>
      </section>
    </div>
  );
}

export default SettingsPage;
