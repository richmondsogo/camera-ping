import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn helper", () => {
  it("keeps both font-size and text-color classes without conflict", () => {
    // (a) cn("text-table","text-foreground") keeps both
    expect(cn("text-table", "text-foreground")).toBe(
      "text-table text-foreground"
    );
  });

  it("overrides control height correctly", () => {
    // (b) cn("h-8","h-7") keeps only h-7
    expect(cn("h-8", "h-7")).toBe("h-7");
  });

  it("overrides border radius within custom rounded group", () => {
    // (c) cn("rounded-control","rounded-dialog") keeps only rounded-dialog
    expect(cn("rounded-control", "rounded-dialog")).toBe("rounded-dialog");
  });

  it("ignores falsy inputs correctly", () => {
    // (d) falsy inputs are ignored
    expect(
      cn("text-table", null, undefined, false, "", "text-foreground")
    ).toBe("text-table text-foreground");
  });

  it("overrides font size within custom font-size group", () => {
    // (e) cn("text-page-title","text-sm") keeps only text-sm (same font-size group)
    expect(cn("text-page-title", "text-sm")).toBe("text-sm");
  });

  it("overrides spacing and width tokens within extended tailwind-merge groups", () => {
    expect(cn("px-gutter", "px-4")).toBe("px-4");
    expect(cn("px-button-x", "px-control-x")).toBe("px-control-x");
    expect(cn("h-8", "h-row-body")).toBe("h-row-body");
    expect(cn("gap-tight", "gap-inline")).toBe("gap-inline");
    expect(cn("w-dialog", "w-full")).toBe("w-full");
    expect(cn("w-full", "w-trigger-status")).toBe("w-trigger-status");
  });
});
