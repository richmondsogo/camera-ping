import { test, expect } from "@playwright/test";

test.describe("Design Tokens & Computed Styles Verification", () => {
  test("asserts computed styles on /_design match token specifications", async ({
    page,
  }) => {
    await page.goto("/_design");

    // 1. Page title typography: 20px / 28px, 600 weight
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

    // 2. Default button: height 32px, radius 6px, font 14/20
    const defaultButton = page.getByTestId("button-default");
    await expect(defaultButton).toBeVisible();
    const defaultBtnBox = await defaultButton.boundingBox();
    expect(defaultBtnBox?.height).toBe(32);
    const defaultBtnStyles = await defaultButton.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
      };
    });
    expect(defaultBtnStyles.borderRadius).toBe("6px");
    expect(defaultBtnStyles.fontSize).toBe("14px");
    expect(defaultBtnStyles.lineHeight).toBe("20px");

    // 3. Small button: height 28px, radius 6px
    const smButton = page.getByTestId("button-sm");
    await expect(smButton).toBeVisible();
    const smBtnBox = await smButton.boundingBox();
    expect(smBtnBox?.height).toBe(28);
    const smBtnStyles = await smButton.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
      };
    });
    expect(smBtnStyles.borderRadius).toBe("6px");

    // 4. Input: height 32px, radius 6px, 1px border
    const input = page.getByTestId("input-default");
    await expect(input).toBeVisible();
    const inputBox = await input.boundingBox();
    expect(inputBox?.height).toBe(32);
    const inputStyles = await input.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
        borderWidth: cs.borderTopWidth,
      };
    });
    expect(inputStyles.borderRadius).toBe("6px");
    expect(inputStyles.borderWidth).toBe("1px");

    // 5. Table cell: font 13px / 18px
    const tableCell = page.getByTestId("table-cell-name");
    await expect(tableCell).toBeVisible();
    const tableCellStyles = await tableCell.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        fontSize: cs.fontSize,
        lineHeight: cs.lineHeight,
      };
    });
    expect(tableCellStyles.fontSize).toBe("13px");
    expect(tableCellStyles.lineHeight).toBe("18px");

    // 6. Page container max-width: 1200px
    const container = page.getByTestId("sample-page-container");
    await expect(container).toBeVisible();
    const containerStyles = await container.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        maxWidth: cs.maxWidth,
      };
    });
    expect(containerStyles.maxWidth).toBe("1200px");

    // 7. Dialog: radius 8px
    const dialogTrigger = page.getByTestId("dialog-trigger-button");
    await dialogTrigger.click();
    const dialogContent = page.getByTestId("dialog-content-box");
    await expect(dialogContent).toBeVisible();
    const dialogStyles = await dialogContent.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        borderRadius: cs.borderRadius,
      };
    });
    expect(dialogStyles.borderRadius).toBe("8px");

    // Close dialog
    await page.keyboard.press("Escape");
    await expect(dialogContent).not.toBeVisible();

    // 8. Local dark toggle operates and unmount cleanup prevents leaking
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
