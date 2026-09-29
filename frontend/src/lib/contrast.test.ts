import { describe, it, expect } from "vitest";
import { getContrastRatio, relativeLuminance, compositeOver } from "./contrast";

describe("WCAG 2.1 Contrast Calculation", () => {
  it("computes black on white as exactly 21:1", () => {
    // black on white = 21
    expect(getContrastRatio([0, 0, 0], [255, 255, 255])).toBe(21);
  });

  it("computes identical colors as exactly 1:1", () => {
    // identical colors = 1
    expect(getContrastRatio([128, 128, 128], [128, 128, 128])).toBe(1);
    expect(getContrastRatio([0, 0, 0], [0, 0, 0])).toBe(1);
    expect(getContrastRatio([255, 255, 255], [255, 255, 255])).toBe(1);
  });

  it("computes a known mid-gray pair accurately", () => {
    // #767676 (118, 118, 118) on white (255, 255, 255) is ~4.54:1
    expect(getContrastRatio([118, 118, 118], [255, 255, 255])).toBe(4.54);
  });

  it("correctly composites semi-transparent color over opaque background", () => {
    // Black with 50% opacity over white -> [128, 128, 128]
    const blended = compositeOver([0, 0, 0, 0.5], [255, 255, 255]);
    expect(blended).toEqual([128, 128, 128]);
  });

  it("calculates relative luminance correctly for extremes", () => {
    expect(relativeLuminance([0, 0, 0])).toBe(0);
    expect(relativeLuminance([255, 255, 255])).toBe(1);
  });
});
