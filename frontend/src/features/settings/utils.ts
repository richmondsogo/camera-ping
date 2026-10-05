export type TimeUnit =
  "seconds" | "minutes" | "hours" | "days" | "weeks" | "months";

export interface UnitDefinition {
  unit: TimeUnit;
  seconds: number;
  label: string;
  singular: string;
  plural: string;
}

export const UNITS: readonly UnitDefinition[] = [
  {
    unit: "months",
    seconds: 2592000, // 30 days = 30 * 86400
    label: "months (30 days)",
    singular: "month",
    plural: "months",
  },
  {
    unit: "weeks",
    seconds: 604800,
    label: "weeks",
    singular: "week",
    plural: "weeks",
  },
  {
    unit: "days",
    seconds: 86400,
    label: "days",
    singular: "day",
    plural: "days",
  },
  {
    unit: "hours",
    seconds: 3600,
    label: "hours",
    singular: "hour",
    plural: "hours",
  },
  {
    unit: "minutes",
    seconds: 60,
    label: "minutes",
    singular: "minute",
    plural: "minutes",
  },
  {
    unit: "seconds",
    seconds: 1,
    label: "seconds",
    singular: "second",
    plural: "seconds",
  },
] as const;

export const UNIT_SELECT_ITEMS = [
  { value: "seconds", label: "seconds" },
  { value: "minutes", label: "minutes" },
  { value: "hours", label: "hours" },
  { value: "days", label: "days" },
  { value: "weeks", label: "weeks" },
  { value: "months", label: "months (30 days)" },
] as const;

export const INTERVAL_PRESETS = [
  { value: "10", label: "10 seconds", seconds: 10 },
  { value: "30", label: "30 seconds", seconds: 30 },
  { value: "60", label: "1 minute", seconds: 60 },
  { value: "120", label: "2 minutes", seconds: 120 },
  { value: "300", label: "5 minutes", seconds: 300 },
  { value: "600", label: "10 minutes", seconds: 600 },
] as const;

export const MIN_INTERVAL_SECONDS = 10;
export const MAX_INTERVAL_SECONDS = 31536000; // 365 days = 365 * 86400

export function toSeconds(amount: number, unit: TimeUnit): number {
  const def = UNITS.find((u) => u.unit === unit);
  if (!def) return amount;
  return amount * def.seconds;
}

export function secondsToCustom(totalSeconds: number): {
  amount: number;
  unit: TimeUnit;
} {
  if (totalSeconds <= 0) {
    return { amount: totalSeconds, unit: "seconds" };
  }

  for (const def of UNITS) {
    if (totalSeconds % def.seconds === 0) {
      return {
        amount: totalSeconds / def.seconds,
        unit: def.unit,
      };
    }
  }

  return { amount: totalSeconds, unit: "seconds" };
}

export function parseAmount(text: string): number | null {
  if (!text || text.trim() === "") {
    return null;
  }

  // Must contain only standard ASCII decimal digits
  if (!/^\d+$/.test(text)) {
    return null;
  }

  if (text.length > 9) {
    return null;
  }

  const num = Number.parseInt(text, 10);
  if (Number.isNaN(num) || num < 0) {
    return null;
  }

  return num;
}

export function validateInterval(
  amountStr: string,
  unit: TimeUnit
): string | null {
  if (!amountStr || amountStr.trim() === "") {
    return "Enter an interval amount.";
  }

  if (!/^\d+$/.test(amountStr) || amountStr.length > 9) {
    return `Enter a whole number of ${unit}.`;
  }

  const amount = Number.parseInt(amountStr, 10);
  if (Number.isNaN(amount) || amount < 0) {
    return `Enter a whole number of ${unit}.`;
  }

  const totalSeconds = toSeconds(amount, unit);
  if (
    totalSeconds < MIN_INTERVAL_SECONDS ||
    totalSeconds > MAX_INTERVAL_SECONDS
  ) {
    return "Choose an interval between 10 seconds and 365 days.";
  }

  return null;
}

export function formatInterval(seconds: number): string {
  const { amount, unit } = secondsToCustom(seconds);
  const def = UNITS.find((u) => u.unit === unit);
  if (!def) {
    return `${amount} seconds`;
  }
  const unitWord = amount === 1 ? def.singular : def.plural;
  return `${amount} ${unitWord}`;
}

const MONTH_NAMES = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

export function formatClockTime(
  dateOrIso: string | Date | number | null | undefined,
  options?: { fallback?: string; now?: Date | number }
): string {
  if (!dateOrIso) {
    return options?.fallback ?? "Never";
  }
  const d = typeof dateOrIso === "object" ? dateOrIso : new Date(dateOrIso);
  if (Number.isNaN(d.getTime())) {
    return options?.fallback ?? "—";
  }

  const current =
    options?.now !== undefined ? new Date(options.now) : new Date();

  const pad = (n: number) => String(n).padStart(2, "0");
  const timeStr = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;

  const isSameDay =
    d.getFullYear() === current.getFullYear() &&
    d.getMonth() === current.getMonth() &&
    d.getDate() === current.getDate();

  if (isSameDay) {
    return timeStr;
  }

  const monthName = MONTH_NAMES[d.getMonth()];
  return `${monthName} ${d.getDate()}, ${timeStr}`;
}
