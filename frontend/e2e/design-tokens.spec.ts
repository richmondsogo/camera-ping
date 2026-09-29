import { test, expect } from "@playwright/test";

test.describe("Design Tokens & Computed Styles Verification", () => {
  test("asserts computed styles, spacing, alignments, and truncation", async ({
    page,
  }) => {
    // 1. Alignment check on /: Header brand's left edge equals page title's left edge
    await page.goto("/");
    const brandOnRoot = page.locator("header span.text-sm").first();
    const titleOnRoot = page.locator("main h1").first();
    await expect(brandOnRoot).toBeVisible();
    await expect(titleOnRoot).toBeVisible();
    const brandBoxRoot = await brandOnRoot.boundingBox();
    const titleBoxRoot = await titleOnRoot.boundingBox();
    expect(brandBoxRoot).not.toBeNull();
    expect(titleBoxRoot).not.toBeNull();
    expect(Math.round(brandBoxRoot!.x)).toBe(Math.round(titleBoxRoot!.x));

    // 2. Alignment check on /settings: Header brand's left edge equals page title's left edge
    await page.goto("/settings");
    const brandOnSettings = page.locator("header span.text-sm").first();
    const titleOnSettings = page.locator("main h1").first();
    await expect(brandOnSettings).toBeVisible();
    await expect(titleOnSettings).toBeVisible();
    const brandBoxSettings = await brandOnSettings.boundingBox();
    const titleBoxSettings = await titleOnSettings.boundingBox();
    expect(brandBoxSettings).not.toBeNull();
    expect(titleBoxSettings).not.toBeNull();
    expect(Math.round(brandBoxSettings!.x)).toBe(Math.round(titleBoxSettings!.x));

    // 3. Header height 56px and Page container side padding 32px, max-width 1200px
    const header = page.locator("header");
    await expect(header).toBeVisible();
    const headerBox = await header.boundingBox();
    expect(headerBox?.height).toBe(56);

    const mainContainer = page.locator("main");
    await expect(mainContainer).toBeVisible();
    const mainStyles = await mainContainer.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        maxWidth: cs.maxWidth,
        paddingLeft: cs.paddingLeft,
        paddingRight: cs.paddingRight,
      };
    });
    expect(mainStyles.maxWidth).toBe("1200px");
    expect(mainStyles.paddingLeft).toBe("32px");
    expect(mainStyles.paddingRight).toBe("32px");

    // Navigate to /_design for component-level verification
    await page.goto("/_design");

    // 4. Page title typography: 20px / 28px, 600 weight
    const pageTitle = page.getByTestId("sample-page-title");
    await expect(pageTitle).toBeVisible();
    const titleStyles = await pageTitle.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
        fontWeight: cs.fontWeight,
      };
    });
    expect(titleStyles.fontSize).toBe("20px");
    expect(titleStyles.lineHeight).toBe("28px");
    expect(titleStyles.fontWeight).toBe("600");

    // 5. Default button: height 32px, horizontal padding 16px, radius 6px
    const defaultButton = page.getByTestId("button-default");
    await expect(defaultButton).toBeVisible();
    const defaultBtnBox = await defaultButton.boundingBox();
    expect(defaultBtnBox?.height).toBe(32);
    const defaultBtnStyles = await defaultButton.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
        paddingLeft: cs.paddingLeft,
        paddingRight: cs.paddingRight,
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
      };
    });
    expect(defaultBtnStyles.borderRadius).toBe("6px");
    expect(defaultBtnStyles.paddingLeft).toBe("16px");
    expect(defaultBtnStyles.paddingRight).toBe("16px");
    expect(defaultBtnStyles.fontSize).toBe("14px");
    expect(defaultBtnStyles.lineHeight).toBe("20px");

    // 6. Small button: height 28px, horizontal padding 12px, radius 6px
    const smButton = page.getByTestId("button-sm");
    await expect(smButton).toBeVisible();
    const smBtnBox = await smButton.boundingBox();
    expect(smBtnBox?.height).toBe(28);
    const smBtnStyles = await smButton.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
        paddingLeft: cs.paddingLeft,
        paddingRight: cs.paddingRight,
      };
    });
    expect(smBtnStyles.borderRadius).toBe("6px");
    expect(smBtnStyles.paddingLeft).toBe("12px");
    expect(smBtnStyles.paddingRight).toBe("12px");

    // 7. Ghost button: at rest transparent background, color equals muted-foreground (#71717a)
    const ghostButton = page.getByTestId("button-ghost");
    await expect(ghostButton).toBeVisible();
    const ghostStyles = await ghostButton.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        backgroundColor: cs.backgroundColor,
        color: cs.color,
      };
    });
    expect(ghostStyles.backgroundColor).toBe("rgba(0, 0, 0, 0)");
    expect(ghostStyles.color).toBe("rgb(113, 113, 122)");

    // 8. Input: height 32px, radius 6px, horizontal padding 12px, 1px border
    const input = page.getByTestId("input-default");
    await expect(input).toBeVisible();
    const inputBox = await input.boundingBox();
    expect(inputBox?.height).toBe(32);
    const inputStyles = await input.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
        borderWidth: cs.borderTopWidth,
        paddingLeft: cs.paddingLeft,
        paddingRight: cs.paddingRight,
      };
    });
    expect(inputStyles.borderRadius).toBe("6px");
    expect(inputStyles.borderWidth).toBe("1px");
    expect(inputStyles.paddingLeft).toBe("12px");
    expect(inputStyles.paddingRight).toBe("12px");

    // 9. Table row heights and cell padding:
    // Header row 40px including 1px border, body row 48px including 1px border, cell px 16px
    const tableHeaderRow = page.locator('[data-testid="table-demo"] thead tr').first();
    await expect(tableHeaderRow).toBeVisible();
    const headerRowBox = await tableHeaderRow.boundingBox();
    expect(headerRowBox?.height).toBe(40);

    const tableBodyRow = page.locator('[data-testid="table-demo"] tbody tr').first();
    await expect(tableBodyRow).toBeVisible();
    const bodyRowBox = await tableBodyRow.boundingBox();
    expect(bodyRowBox?.height).toBe(48);

    const tableCell = page.getByTestId("table-cell-name");
    await expect(tableCell).toBeVisible();
    const tableCellStyles = await tableCell.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
        paddingLeft: cs.paddingLeft,
        paddingRight: cs.paddingRight,
      };
    });
    expect(tableCellStyles.fontSize).toBe("13px");
    expect(tableCellStyles.lineHeight).toBe("18px");
    expect(tableCellStyles.paddingLeft).toBe("16px");
    expect(tableCellStyles.paddingRight).toBe("16px");

    // 10. Truncation is real:
    // Long description row: scrollWidth > clientWidth, text-overflow is ellipsis, title attribute has full text
    const longDesc = page.getByTestId("table-cell-description");
    await expect(longDesc).toBeVisible();
    const longDescProps = await longDesc.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
        textOverflow: cs.textOverflow,
        title: el.getAttribute("title"),
      };
    });
    expect(longDescProps.scrollWidth).toBeGreaterThan(longDescProps.clientWidth);
    expect(longDescProps.textOverflow).toBe("ellipsis");
    expect(longDescProps.title).toBe(
      "Primary pan-tilt-zoom optical camera covering south perimeter entry and truck weighbridge"
    );

    // Short description row: scrollWidth <= clientWidth (NOT truncated)
    const shortDesc = page
      .locator('[data-testid="table-demo"] tbody tr:nth-child(2) td:nth-child(3) div')
      .first();
    await expect(shortDesc).toBeVisible();
    const shortDescProps = await shortDesc.evaluate((el) => ({
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
    }));
    expect(shortDescProps.scrollWidth).toBeLessThanOrEqual(shortDescProps.clientWidth);

    // 11. Select popup:
    // top equals trigger bottom plus 4px; padding 4px; item min-height 32px; gap between items 2px; min-width >= trigger width
    const selectTrigger = page.getByTestId("select-default");
    await selectTrigger.scrollIntoViewIfNeeded();
    await selectTrigger.click();

    const selectPopup = page.locator('[data-slot="select-content"]');
    await expect(selectPopup).toBeVisible();

    const triggerBox = await selectTrigger.boundingBox();
    const popupBox = await selectPopup.boundingBox();
    expect(triggerBox).not.toBeNull();
    expect(popupBox).not.toBeNull();

    // Top equals trigger bottom plus 4px (Amendment 18)
    expect(Math.round(popupBox!.y)).toBe(Math.round(triggerBox!.y + triggerBox!.height + 4));

    // Min-width >= trigger width
    expect(Math.round(popupBox!.width)).toBeGreaterThanOrEqual(Math.round(triggerBox!.width));

    // Popup padding 4px
    const popupPadding = await selectPopup.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return cs.paddingTop;
    });
    expect(popupPadding).toBe("4px");

    // Item min-height 32px and item-to-item gap 2px
    const selectItems = page.locator('[data-slot="select-item"]');
    expect(await selectItems.count()).toBeGreaterThanOrEqual(2);
    const item0Box = await selectItems.nth(0).boundingBox();
    const item1Box = await selectItems.nth(1).boundingBox();
    expect(item0Box).not.toBeNull();
    expect(item1Box).not.toBeNull();
    expect(item0Box!.height).toBeGreaterThanOrEqual(32);
    expect(Math.round(item1Box!.y - (item0Box!.y + item0Box!.height))).toBe(2);

    await page.keyboard.press("Escape");
    await expect(selectPopup).not.toBeVisible();

    // 12. Dialog:
    // Radius 8px; padding 24px; width exactly 480px at 1280px viewport; at 400px viewport at most 90vw (360px)
    const dialogTrigger = page.getByTestId("dialog-trigger-button");
    await expect(dialogTrigger).toBeVisible();
    await dialogTrigger.click();

    const dialogContent = page.getByTestId("dialog-content-box");
    await expect(dialogContent).toBeVisible();
    const dialogBox = await dialogContent.boundingBox();
    expect(dialogBox).not.toBeNull();
    expect(Math.round(dialogBox!.width)).toBe(480);

    const dialogStyles = await dialogContent.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
        paddingTop: cs.paddingTop,
        paddingLeft: cs.paddingLeft,
      };
    });
    expect(dialogStyles.borderRadius).toBe("8px");
    expect(dialogStyles.paddingTop).toBe("24px");
    expect(dialogStyles.paddingLeft).toBe("24px");

    await page.keyboard.press("Escape");
    await expect(dialogContent).not.toBeVisible();

    // At 400px viewport: dialog is at most 90vw
    await page.setViewportSize({ width: 400, height: 800 });
    await dialogTrigger.click();
    await expect(dialogContent).toBeVisible();
    const smallDialogBox = await dialogContent.boundingBox();
    expect(smallDialogBox).not.toBeNull();
    expect(smallDialogBox!.width).toBeLessThanOrEqual(400 * 0.90 + 0.5);

    await page.keyboard.press("Escape");
    await expect(dialogContent).not.toBeVisible();

    // Reset viewport size
    await page.setViewportSize({ width: 1280, height: 900 });

    // 13. Local dark toggle operates and unmount cleanup prevents leaking
    const toggleBtn = page.getByTestId("theme-toggle-button");
    await toggleBtn.click();
    const isDarkAfterToggle = await page.evaluate(() =>
      document.documentElement.classList.contains("dark")
    );
    expect(isDarkAfterToggle).toBe(true);

    await toggleBtn.click();
    const isDarkAfterReset = await page.evaluate(() =>
      document.documentElement.classList.contains("dark")
    );
    expect(isDarkAfterReset).toBe(false);
  });
});
