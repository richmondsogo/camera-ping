import { test, expect, Page } from "@playwright/test";

interface ContrastResult {
  name: string;
  fgHex: string;
  bgHex: string;
  ratio: number;
  threshold: number;
  pass: boolean;
}

// Client-side evaluation helper for measuring contrast using Canvas 2D
const CLIENT_EVALUATOR_SCRIPT = `
(() => {
  const canvas = document.createElement("canvas");
  canvas.width = 1;
  canvas.height = 1;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });

  const disableTransitionsStyle = document.createElement("style");
  disableTransitionsStyle.textContent = "*, *::before, *::after { transition: none !important; animation: none !important; }";
  if (document.head) document.head.appendChild(disableTransitionsStyle);

  function parseColor(colorStr) {
    if (!colorStr || colorStr === "transparent" || colorStr === "rgba(0, 0, 0, 0)") {
      return [0, 0, 0, 0];
    }
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = colorStr;
    ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255];
  }

  function getEffectiveBg(el) {
    const layers = [];
    let curr = el;
    while (curr && curr !== document.documentElement) {
      const cs = window.getComputedStyle(curr);
      const bg = parseColor(cs.backgroundColor);
      if (bg[3] > 0) {
        layers.push(bg);
        if (bg[3] >= 0.99) break;
      }
      curr = curr.parentElement;
    }
    const rootCs = window.getComputedStyle(document.documentElement);
    const rootBg = parseColor(rootCs.backgroundColor);
    if (rootBg[3] > 0) {
      layers.push(rootBg);
    } else {
      const isDark = document.documentElement.classList.contains("dark");
      layers.push(isDark ? [9, 9, 11, 1] : [255, 255, 255, 1]);
    }

    let comp = [
      layers[layers.length - 1][0],
      layers[layers.length - 1][1],
      layers[layers.length - 1][2],
    ];
    for (let i = layers.length - 2; i >= 0; i--) {
      const fg = layers[i];
      const a = fg[3];
      comp = [
        Math.round(fg[0] * a + comp[0] * (1 - a)),
        Math.round(fg[1] * a + comp[1] * (1 - a)),
        Math.round(fg[2] * a + comp[2] * (1 - a)),
      ];
    }
    return comp;
  }

  function getEffectiveText(el, bgRgb, pseudo = null) {
    const cs = window.getComputedStyle(el, pseudo);
    const fg = parseColor(cs.color);
    let totalOpacity = 1;
    let curr = el;
    while (curr && curr !== document.documentElement) {
      const curCs = window.getComputedStyle(curr);
      totalOpacity *= parseFloat(curCs.opacity || "1");
      curr = curr.parentElement;
    }
    const a = fg[3] * totalOpacity;
    return [
      Math.round(fg[0] * a + bgRgb[0] * (1 - a)),
      Math.round(fg[1] * a + bgRgb[1] * (1 - a)),
      Math.round(fg[2] * a + bgRgb[2] * (1 - a)),
    ];
  }

  function channelLum(c) {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  }

  function relLum(rgb) {
    return 0.2126 * channelLum(rgb[0]) + 0.7152 * channelLum(rgb[1]) + 0.0722 * channelLum(rgb[2]);
  }

  function calcRatio(c1, c2) {
    const l1 = relLum(c1);
    const l2 = relLum(c2);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return Math.round(((lighter + 0.05) / (darker + 0.05)) * 100) / 100;
  }

  function toHex(rgb) {
    const h = (n) => n.toString(16).padStart(2, "0");
    return '#' + h(rgb[0]) + h(rgb[1]) + h(rgb[2]);
  }

  window.__contrastTools = {
    parseColor,
    getEffectiveBg,
    getEffectiveText,
    calcRatio,
    toHex,
  };
})();
`;

async function setupPageTools(page: Page, isDark: boolean) {
  await page.evaluate(CLIENT_EVALUATOR_SCRIPT);
  if (isDark) {
    await page.evaluate(() => document.documentElement.classList.add("dark"));
  } else {
    await page.evaluate(() =>
      document.documentElement.classList.remove("dark")
    );
  }
}

async function measureElement(
  page: Page,
  selector: string,
  options: {
    name: string;
    threshold: number;
    pseudo?: string;
    measureType?: "text" | "border" | "ring" | "dot" | "overlay";
    containerSelector?: string;
  }
): Promise<ContrastResult> {
  const loc = page.locator(selector).first();
  await loc.waitFor({ state: "attached", timeout: 5000 });
  const count = await loc.count();
  if (count === 0) {
    throw new Error(
      `Selector not found for pair "${options.name}": ${selector}`
    );
  }

  const data = await loc.evaluate((el, opts) => {
    const tools = (
      window as unknown as {
        __contrastTools: {
          parseColor: (c: string) => [number, number, number, number];
          getEffectiveBg: (el: Element) => [number, number, number];
          getEffectiveText: (
            el: Element,
            bg: [number, number, number],
            pseudo?: string | null
          ) => [number, number, number];
          calcRatio: (
            c1: [number, number, number],
            c2: [number, number, number]
          ) => number;
          toHex: (rgb: [number, number, number]) => string;
        };
      }
    ).__contrastTools;

    const type = opts.measureType || "text";
    let fgRgb: [number, number, number];
    let bgRgb: [number, number, number];

    if (type === "text") {
      bgRgb = tools.getEffectiveBg(el);
      fgRgb = tools.getEffectiveText(el, bgRgb, opts.pseudo || null);
    } else if (type === "border") {
      // Border against surrounding background
      const container = opts.containerSelector
        ? document.querySelector(opts.containerSelector)
        : el.parentElement;
      bgRgb = tools.getEffectiveBg(container || el.parentElement || el);
      const cs = window.getComputedStyle(el);
      const borderColor = tools.parseColor(cs.borderTopColor || cs.borderColor);
      fgRgb = [borderColor[0], borderColor[1], borderColor[2]];
    } else if (type === "ring") {
      const cs = window.getComputedStyle(el);
      const ringStr =
        cs.getPropertyValue("--color-ring").trim() ||
        cs.getPropertyValue("--ring").trim() ||
        cs.outlineColor;
      const ringParsed = tools.parseColor(ringStr);
      fgRgb = [ringParsed[0], ringParsed[1], ringParsed[2]];
      const container = opts.containerSelector
        ? document.querySelector(opts.containerSelector)
        : el.parentElement;
      bgRgb = tools.getEffectiveBg(container || el.parentElement || el);
    } else if (type === "dot") {
      const dot = el.querySelector("span[aria-hidden='true']") || el;
      const cs = window.getComputedStyle(dot);
      const dotColor = tools.parseColor(cs.backgroundColor);
      fgRgb = [dotColor[0], dotColor[1], dotColor[2]];
      bgRgb = tools.getEffectiveBg(el.parentElement || el);
    } else if (type === "overlay") {
      // Overlay backdrop background against page body
      const cs = window.getComputedStyle(el);
      const overlayColor = tools.parseColor(cs.backgroundColor);
      // Alpha blend overlay over pure canvas
      const isDark = document.documentElement.classList.contains("dark");
      const baseCanvas: [number, number, number] = isDark
        ? [9, 9, 11]
        : [255, 255, 255];
      const blended: [number, number, number] = [
        Math.round(
          overlayColor[0] * overlayColor[3] +
            baseCanvas[0] * (1 - overlayColor[3])
        ),
        Math.round(
          overlayColor[1] * overlayColor[3] +
            baseCanvas[1] * (1 - overlayColor[3])
        ),
        Math.round(
          overlayColor[2] * overlayColor[3] +
            baseCanvas[2] * (1 - overlayColor[3])
        ),
      ];
      fgRgb = blended;
      bgRgb = baseCanvas;
    } else {
      throw new Error(`Unknown measureType: ${type}`);
    }

    const ratio = tools.calcRatio(fgRgb, bgRgb);
    return {
      fgHex: tools.toHex(fgRgb),
      bgHex: tools.toHex(bgRgb),
      ratio,
    };
  }, options);

  return {
    name: options.name,
    fgHex: data.fgHex,
    bgHex: data.bgHex,
    ratio: data.ratio,
    threshold: options.threshold,
    pass: data.ratio >= options.threshold,
  };
}

function formatResultsTable(mode: string, results: ContrastResult[]): string {
  const header =
    `\n### Contrast Measurement Table: ${mode.toUpperCase()} MODE\n` +
    `| Element / Pair | Foreground | Background | Ratio | Threshold | Status |\n` +
    `| :--- | :--- | :--- | :--- | :--- | :--- |\n`;
  const rows = results
    .map(
      (r) =>
        `| ${r.name} | \`${r.fgHex}\` | \`${r.bgHex}\` | **${r.ratio}:1** | ${r.threshold}:1 | ${r.pass ? "PASS" : "FAIL"} |`
    )
    .join("\n");
  return header + rows + "\n";
}

test.describe("WCAG 2.1 Contrast Measurements", () => {
  test("measures all design system pairs in Light mode", async ({ page }) => {
    await page.addInitScript(CLIENT_EVALUATOR_SCRIPT);
    await page.goto("/_design");
    await page
      .locator('[data-testid="styleguide-page"]')
      .waitFor({ state: "visible" });
    await setupPageTools(page, false);

    const results: ContrastResult[] = [];

    // 1-11 Buttons & hover states
    results.push(
      await measureElement(page, '[data-testid="button-default"]', {
        name: "Button: Default",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-default"]');
    results.push(
      await measureElement(page, '[data-testid="button-default"]', {
        name: "Button: Default (hover)",
        threshold: 4.5,
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-secondary"]', {
        name: "Button: Secondary",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-secondary"]');
    results.push(
      await measureElement(page, '[data-testid="button-secondary"]', {
        name: "Button: Secondary (hover)",
        threshold: 4.5,
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-outline"]', {
        name: "Button: Outline",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-outline"]');
    results.push(
      await measureElement(page, '[data-testid="button-outline"]', {
        name: "Button: Outline (hover)",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="button-outline"]', {
        name: "Button: Outline border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-ghost"]', {
        name: "Button: Ghost",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-ghost"]');
    results.push(
      await measureElement(page, '[data-testid="button-ghost"]', {
        name: "Button: Ghost (hover)",
        threshold: 4.5,
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-destructive"]', {
        name: "Button: Destructive",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-destructive"]');
    results.push(
      await measureElement(page, '[data-testid="button-destructive"]', {
        name: "Button: Destructive (hover)",
        threshold: 4.5,
      })
    );

    // 12-15 Badges
    results.push(
      await measureElement(page, '[data-testid="badge-default"]', {
        name: "Badge: Default",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="badge-secondary"]', {
        name: "Badge: Secondary",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="badge-outline"]', {
        name: "Badge: Outline",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="badge-destructive"]', {
        name: "Badge: Destructive",
        threshold: 4.5,
      })
    );

    // 16-18 Input
    results.push(
      await measureElement(page, '[data-testid="input-default"]', {
        name: "Input: Value text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="input-placeholder"]', {
        name: "Input: Placeholder text",
        threshold: 4.5,
        pseudo: "::placeholder",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="input-default"]', {
        name: "Input: Border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    // Textarea
    results.push(
      await measureElement(page, '[data-testid="textarea-default"]', {
        name: "Textarea: Value text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="textarea-placeholder"]', {
        name: "Textarea: Placeholder text",
        threshold: 4.5,
        pseudo: "::placeholder",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="textarea-default"]', {
        name: "Textarea: Border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    // Form states
    results.push(
      await measureElement(page, '[data-testid="form-error-text"]', {
        name: "Form: Error text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="input-error"]', {
        name: "Form: Invalid border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    // Select
    results.push(
      await measureElement(page, '[data-testid="select-default"]', {
        name: "Select: Trigger text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="select-default"]', {
        name: "Select: Trigger border",
        threshold: 3.0,
        measureType: "border",
      })
    );
    // Open select to measure item and highlight
    await page.click('[data-testid="select-default"]');
    const selectItem = page.locator('[data-slot="select-item"]').first();
    await expect(selectItem).toBeVisible();
    results.push(
      await measureElement(page, '[data-slot="select-item"]', {
        name: "Select: Popup item text",
        threshold: 4.5,
      })
    );
    await page.hover('[data-slot="select-item"]');
    results.push(
      await measureElement(page, '[data-slot="select-item"]', {
        name: "Select: Popup item (highlighted)",
        threshold: 4.5,
      })
    );
    await page.keyboard.press("Escape");

    // Dialog
    results.push(
      await measureElement(page, '[data-testid="dialog-trigger-button"]', {
        name: "Dialog: Trigger button",
        threshold: 4.5,
      })
    );
    await page.click('[data-testid="dialog-trigger-button"]');
    await expect(
      page.locator('[data-testid="dialog-content-box"]')
    ).toBeVisible();
    results.push(
      await measureElement(page, '[data-testid="dialog-description-box"]', {
        name: "Dialog: Content text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="dialog-error-text"]', {
        name: "Form: Error text (inside dialog)",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-slot="dialog-overlay"]', {
        name: "Dialog: Overlay backdrop",
        threshold: 1.0,
        measureType: "overlay",
      })
    );
    await page.keyboard.press("Escape");
    await expect(
      page.locator('[data-testid="dialog-content-box"]')
    ).not.toBeVisible();

    // Typography
    results.push(
      await measureElement(page, '[data-testid="sample-body"]', {
        name: "Typography: Foreground text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="sample-small"]', {
        name: "Typography: Muted-foreground text",
        threshold: 4.5,
      })
    );

    // Table
    results.push(
      await measureElement(page, '[data-testid="table-head-name"]', {
        name: "Table: Header text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="table-cell-name"]', {
        name: "Table: Cell text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="table-cell-description"]', {
        name: "Table: Description cell text",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="table-row-sample"]');
    results.push(
      await measureElement(page, '[data-testid="table-cell-name"]', {
        name: "Table: Row hover cell text",
        threshold: 4.5,
      })
    );

    // Navigation (on /)
    await page.goto("/");
    await page
      .locator('[data-testid="nav-dashboard"]')
      .waitFor({ state: "visible" });
    await setupPageTools(page, false);
    results.push(
      await measureElement(page, '[data-testid="nav-dashboard"]', {
        name: "Navigation: Active link",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="nav-settings"]', {
        name: "Navigation: Inactive link",
        threshold: 4.5,
      })
    );

    // Focus Rings (return to /_design)
    await page.goto("/_design");
    await page
      .locator('[data-testid="styleguide-page"]')
      .waitFor({ state: "visible" });
    await setupPageTools(page, false);
    const btn = page.getByTestId("button-default");
    await btn.focus();
    results.push(
      await measureElement(page, '[data-testid="button-default"]', {
        name: "Focus Ring: Button",
        threshold: 3.0,
        measureType: "ring",
      })
    );
    const inp = page.getByTestId("input-default");
    await inp.focus();
    results.push(
      await measureElement(page, '[data-testid="input-default"]', {
        name: "Focus Ring: Input",
        threshold: 3.0,
        measureType: "ring",
      })
    );
    const txt = page.getByTestId("textarea-default");
    await txt.focus();
    results.push(
      await measureElement(page, '[data-testid="textarea-default"]', {
        name: "Textarea: Focus ring",
        threshold: 3.0,
        measureType: "ring",
      })
    );
    const sel = page.getByTestId("select-default");
    await sel.focus();
    results.push(
      await measureElement(page, '[data-testid="select-default"]', {
        name: "Focus Ring: Select",
        threshold: 3.0,
        measureType: "ring",
      })
    );

    // Status indicators
    results.push(
      await measureElement(page, '[data-testid="status-online"]', {
        name: "Status: Online dot",
        threshold: 3.0,
        measureType: "dot",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="status-offline"]', {
        name: "Status: Offline dot",
        threshold: 3.0,
        measureType: "dot",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="status-unknown"]', {
        name: "Status: Unknown dot",
        threshold: 3.0,
        measureType: "dot",
      })
    );

    // Assert exact N pairs measured (non-vacuous: 46 pairs)
    expect(results.length).toBe(46);

    const failures = results.filter((r) => !r.pass);
    if (process.env.CONTRAST_REPORT === "1" || failures.length > 0) {
      console.log(formatResultsTable("Light", results));
    }

    if (failures.length > 0) {
      console.warn(
        `[LIGHT MODE] ${failures.length} contrast failure(s) found.`
      );
    }
    // Strict assertion:
    expect(
      failures,
      `Failing pairs in Light mode: ${failures.map((f) => f.name + " (" + f.ratio + ":1 < " + f.threshold + ":1)").join(", ")}`
    ).toHaveLength(0);
  });

  test("measures all design system pairs in Dark mode", async ({ page }) => {
    await page.addInitScript(CLIENT_EVALUATOR_SCRIPT);
    await page.addInitScript(() =>
      document.documentElement.classList.add("dark")
    );
    await page.goto("/_design");
    await page
      .locator('[data-testid="styleguide-page"]')
      .waitFor({ state: "visible" });
    await setupPageTools(page, true);

    const results: ContrastResult[] = [];

    // 1-11 Buttons & hover states
    results.push(
      await measureElement(page, '[data-testid="button-default"]', {
        name: "Button: Default",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-default"]');
    results.push(
      await measureElement(page, '[data-testid="button-default"]', {
        name: "Button: Default (hover)",
        threshold: 4.5,
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-secondary"]', {
        name: "Button: Secondary",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-secondary"]');
    results.push(
      await measureElement(page, '[data-testid="button-secondary"]', {
        name: "Button: Secondary (hover)",
        threshold: 4.5,
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-outline"]', {
        name: "Button: Outline",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-outline"]');
    results.push(
      await measureElement(page, '[data-testid="button-outline"]', {
        name: "Button: Outline (hover)",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="button-outline"]', {
        name: "Button: Outline border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-ghost"]', {
        name: "Button: Ghost",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-ghost"]');
    results.push(
      await measureElement(page, '[data-testid="button-ghost"]', {
        name: "Button: Ghost (hover)",
        threshold: 4.5,
      })
    );

    results.push(
      await measureElement(page, '[data-testid="button-destructive"]', {
        name: "Button: Destructive",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="button-destructive"]');
    results.push(
      await measureElement(page, '[data-testid="button-destructive"]', {
        name: "Button: Destructive (hover)",
        threshold: 4.5,
      })
    );

    // 12-15 Badges
    results.push(
      await measureElement(page, '[data-testid="badge-default"]', {
        name: "Badge: Default",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="badge-secondary"]', {
        name: "Badge: Secondary",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="badge-outline"]', {
        name: "Badge: Outline",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="badge-destructive"]', {
        name: "Badge: Destructive",
        threshold: 4.5,
      })
    );

    // 16-18 Input
    results.push(
      await measureElement(page, '[data-testid="input-default"]', {
        name: "Input: Value text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="input-placeholder"]', {
        name: "Input: Placeholder text",
        threshold: 4.5,
        pseudo: "::placeholder",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="input-default"]', {
        name: "Input: Border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    // Textarea
    results.push(
      await measureElement(page, '[data-testid="textarea-default"]', {
        name: "Textarea: Value text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="textarea-placeholder"]', {
        name: "Textarea: Placeholder text",
        threshold: 4.5,
        pseudo: "::placeholder",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="textarea-default"]', {
        name: "Textarea: Border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    // Form states
    results.push(
      await measureElement(page, '[data-testid="form-error-text"]', {
        name: "Form: Error text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="input-error"]', {
        name: "Form: Invalid border",
        threshold: 3.0,
        measureType: "border",
      })
    );

    // Select
    results.push(
      await measureElement(page, '[data-testid="select-default"]', {
        name: "Select: Trigger text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="select-default"]', {
        name: "Select: Trigger border",
        threshold: 3.0,
        measureType: "border",
      })
    );
    await page.click('[data-testid="select-default"]');
    const selectItem = page.locator('[data-slot="select-item"]').first();
    await expect(selectItem).toBeVisible();
    results.push(
      await measureElement(page, '[data-slot="select-item"]', {
        name: "Select: Popup item text",
        threshold: 4.5,
      })
    );
    await page.hover('[data-slot="select-item"]');
    results.push(
      await measureElement(page, '[data-slot="select-item"]', {
        name: "Select: Popup item (highlighted)",
        threshold: 4.5,
      })
    );
    await page.keyboard.press("Escape");

    // Dialog
    results.push(
      await measureElement(page, '[data-testid="dialog-trigger-button"]', {
        name: "Dialog: Trigger button",
        threshold: 4.5,
      })
    );
    await page.click('[data-testid="dialog-trigger-button"]');
    await expect(
      page.locator('[data-testid="dialog-content-box"]')
    ).toBeVisible();
    results.push(
      await measureElement(page, '[data-testid="dialog-description-box"]', {
        name: "Dialog: Content text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="dialog-error-text"]', {
        name: "Form: Error text (inside dialog)",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-slot="dialog-overlay"]', {
        name: "Dialog: Overlay backdrop",
        threshold: 1.0,
        measureType: "overlay",
      })
    );
    await page.keyboard.press("Escape");
    await expect(
      page.locator('[data-testid="dialog-content-box"]')
    ).not.toBeVisible();

    // Typography
    results.push(
      await measureElement(page, '[data-testid="sample-body"]', {
        name: "Typography: Foreground text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="sample-small"]', {
        name: "Typography: Muted-foreground text",
        threshold: 4.5,
      })
    );

    // Table
    results.push(
      await measureElement(page, '[data-testid="table-head-name"]', {
        name: "Table: Header text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="table-cell-name"]', {
        name: "Table: Cell text",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="table-cell-description"]', {
        name: "Table: Description cell text",
        threshold: 4.5,
      })
    );
    await page.hover('[data-testid="table-row-sample"]');
    results.push(
      await measureElement(page, '[data-testid="table-cell-name"]', {
        name: "Table: Row hover cell text",
        threshold: 4.5,
      })
    );

    // Navigation (on /)
    await page.goto("/");
    await page
      .locator('[data-testid="nav-dashboard"]')
      .waitFor({ state: "visible" });
    await setupPageTools(page, true);
    results.push(
      await measureElement(page, '[data-testid="nav-dashboard"]', {
        name: "Navigation: Active link",
        threshold: 4.5,
      })
    );
    results.push(
      await measureElement(page, '[data-testid="nav-settings"]', {
        name: "Navigation: Inactive link",
        threshold: 4.5,
      })
    );

    // Focus Rings (return to /_design)
    await page.goto("/_design");
    await page
      .locator('[data-testid="styleguide-page"]')
      .waitFor({ state: "visible" });
    await setupPageTools(page, true);
    const btn = page.getByTestId("button-default");
    await btn.focus();
    results.push(
      await measureElement(page, '[data-testid="button-default"]', {
        name: "Focus Ring: Button",
        threshold: 3.0,
        measureType: "ring",
      })
    );
    const inp = page.getByTestId("input-default");
    await inp.focus();
    results.push(
      await measureElement(page, '[data-testid="input-default"]', {
        name: "Focus Ring: Input",
        threshold: 3.0,
        measureType: "ring",
      })
    );
    const txt = page.getByTestId("textarea-default");
    await txt.focus();
    results.push(
      await measureElement(page, '[data-testid="textarea-default"]', {
        name: "Textarea: Focus ring",
        threshold: 3.0,
        measureType: "ring",
      })
    );
    const sel = page.getByTestId("select-default");
    await sel.focus();
    results.push(
      await measureElement(page, '[data-testid="select-default"]', {
        name: "Focus Ring: Select",
        threshold: 3.0,
        measureType: "ring",
      })
    );

    // Status indicators
    results.push(
      await measureElement(page, '[data-testid="status-online"]', {
        name: "Status: Online dot",
        threshold: 3.0,
        measureType: "dot",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="status-offline"]', {
        name: "Status: Offline dot",
        threshold: 3.0,
        measureType: "dot",
      })
    );
    results.push(
      await measureElement(page, '[data-testid="status-unknown"]', {
        name: "Status: Unknown dot",
        threshold: 3.0,
        measureType: "dot",
      })
    );

    // Assert exact N pairs measured (non-vacuous: 46 pairs)
    expect(results.length).toBe(46);

    const failures = results.filter((r) => !r.pass);
    if (process.env.CONTRAST_REPORT === "1" || failures.length > 0) {
      console.log(formatResultsTable("Dark", results));
    }

    if (failures.length > 0) {
      console.warn(`[DARK MODE] ${failures.length} contrast failure(s) found.`);
    }
    // Strict assertion:
    expect(
      failures,
      `Failing pairs in Dark mode: ${failures.map((f) => f.name + " (" + f.ratio + ":1 < " + f.threshold + ":1)").join(", ")}`
    ).toHaveLength(0);
  });
});
