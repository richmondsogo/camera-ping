import { describe, expect, it } from "vitest";
import {
  formatClockTime,
  formatInterval,
  parseAmount,
  secondsToCustom,
  toSeconds,
  validateInterval,
} from "./utils";

describe("settings utils", () => {
  describe("toSeconds", () => {
    it("converts amount and unit to seconds", () => {
      expect(toSeconds(10, "seconds")).toBe(10);
      expect(toSeconds(1, "minutes")).toBe(60);
      expect(toSeconds(5, "minutes")).toBe(300);
      expect(toSeconds(2, "hours")).toBe(7200);
      expect(toSeconds(1, "days")).toBe(86400);
      expect(toSeconds(2, "weeks")).toBe(1209600);
      expect(toSeconds(1, "months")).toBe(2592000);
    });
  });

  describe("secondsToCustom", () => {
    it("converts seconds to the largest exact unit matching requirement", () => {
      // Requirements specified:
      // 7200 -> 2 hours
      // 90 -> 90 seconds
      // 86400 -> 1 day
      // 604800 -> 1 week
      // 2592000 -> 1 month
      // 45 -> 45 seconds
      // 10 -> 10 seconds
      // 31536000 -> 365 days
      expect(secondsToCustom(7200)).toEqual({ amount: 2, unit: "hours" });
      expect(secondsToCustom(90)).toEqual({ amount: 90, unit: "seconds" });
      expect(secondsToCustom(86400)).toEqual({ amount: 1, unit: "days" });
      expect(secondsToCustom(604800)).toEqual({ amount: 1, unit: "weeks" });
      expect(secondsToCustom(2592000)).toEqual({ amount: 1, unit: "months" });
      expect(secondsToCustom(45)).toEqual({ amount: 45, unit: "seconds" });
      expect(secondsToCustom(10)).toEqual({ amount: 10, unit: "seconds" });
      expect(secondsToCustom(31536000)).toEqual({ amount: 365, unit: "days" });

      // Presets
      expect(secondsToCustom(60)).toEqual({ amount: 1, unit: "minutes" });
      expect(secondsToCustom(120)).toEqual({ amount: 2, unit: "minutes" });
      expect(secondsToCustom(300)).toEqual({ amount: 5, unit: "minutes" });
      expect(secondsToCustom(600)).toEqual({ amount: 10, unit: "minutes" });
    });
  });

  describe("parseAmount", () => {
    it("parses valid ASCII digits", () => {
      expect(parseAmount("10")).toBe(10);
      expect(parseAmount("0")).toBe(0);
      expect(parseAmount("999999999")).toBe(999999999);
    });

    it("rejects non-digit and invalid formats", () => {
      expect(parseAmount("")).toBeNull();
      expect(parseAmount(" 5")).toBeNull();
      expect(parseAmount("5 ")).toBeNull();
      expect(parseAmount("-5")).toBeNull();
      expect(parseAmount("2.5")).toBeNull();
      expect(parseAmount("1e3")).toBeNull();
      expect(parseAmount("abc")).toBeNull();
      expect(parseAmount("٣")).toBeNull(); // Non-ASCII Arabic-Indic digit
      expect(parseAmount("1000000000")).toBeNull(); // 10 digits (> 9 digits)
    });
  });

  describe("validateInterval", () => {
    it("returns null for valid intervals", () => {
      expect(validateInterval("10", "seconds")).toBeNull();
      expect(validateInterval("1", "minutes")).toBeNull();
      expect(validateInterval("2", "hours")).toBeNull();
      expect(validateInterval("365", "days")).toBeNull();
    });

    it("returns appropriate error message for empty input", () => {
      expect(validateInterval("", "seconds")).toBe("Enter an interval amount.");
    });

    it("returns error for invalid number formatting", () => {
      expect(validateInterval("abc", "seconds")).toBe(
        "Enter a whole number of seconds."
      );
      expect(validateInterval("2.5", "minutes")).toBe(
        "Enter a whole number of minutes."
      );
      expect(validateInterval("-5", "hours")).toBe(
        "Enter a whole number of hours."
      );
      expect(validateInterval(" 5", "days")).toBe(
        "Enter a whole number of days."
      );
      expect(validateInterval("1234567890", "seconds")).toBe(
        "Enter a whole number of seconds."
      );
    });

    it("returns error for out-of-bounds intervals", () => {
      const boundsError = "Choose an interval between 10 seconds and 365 days.";
      // Less than 10 seconds
      expect(validateInterval("9", "seconds")).toBe(boundsError);
      expect(validateInterval("0", "seconds")).toBe(boundsError);
      // Greater than 365 days (31536000 seconds)
      expect(validateInterval("366", "days")).toBe(boundsError);
      expect(validateInterval("13", "months")).toBe(boundsError); // 13 * 30 * 86400 = 33696000
    });
  });

  describe("formatInterval", () => {
    it("formats seconds into readable strings", () => {
      expect(formatInterval(10)).toBe("10 seconds");
      expect(formatInterval(45)).toBe("45 seconds");
      expect(formatInterval(60)).toBe("1 minute");
      expect(formatInterval(120)).toBe("2 minutes");
      expect(formatInterval(3600)).toBe("1 hour");
      expect(formatInterval(7200)).toBe("2 hours");
      expect(formatInterval(86400)).toBe("1 day");
      expect(formatInterval(172800)).toBe("2 days");
      expect(formatInterval(604800)).toBe("1 week");
      expect(formatInterval(1209600)).toBe("2 weeks");
      expect(formatInterval(2592000)).toBe("1 month");
      expect(formatInterval(5184000)).toBe("2 months");
      expect(formatInterval(31536000)).toBe("365 days");
    });
  });

  describe("formatClockTime", () => {
    it("returns fallback for null or undefined", () => {
      expect(formatClockTime(null)).toBe("Never");
      expect(formatClockTime(undefined, { fallback: "—" })).toBe("—");
      expect(formatClockTime("invalid-date")).toBe("—");
    });

    it("formats same-day timestamps as HH:mm:ss", () => {
      const now = new Date("2026-10-05T15:30:00Z");
      const sameDayIso = "2026-10-05T08:15:22Z";
      const formatted = formatClockTime(sameDayIso, { now });
      // Should not include month name or year
      expect(formatted).not.toMatch(/Oct|2026/);
      expect(formatted).toMatch(/\d{2}:\d{2}:\d{2}/);
    });

    it("formats different-day timestamps with date and time", () => {
      const now = new Date("2026-10-05T15:30:00Z");
      const diffDayIso = "2026-10-06T15:30:00Z";
      const formatted = formatClockTime(diffDayIso, { now });
      // Should include month name
      expect(formatted).toMatch(/Oct/);
      expect(formatted).toMatch(/\d{2}:\d{2}:\d{2}/);
    });
  });
});
