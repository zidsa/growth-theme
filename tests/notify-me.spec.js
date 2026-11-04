import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const storeOrigin = "https://store.test";
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));

const productSection = (productId) => `
  <div id="product-main-section">
    <input type="hidden" id="product-id" value="${productId}" />
    <button type="button" command="show-modal" commandfor="notify-me-dialog">Notify me</button>
  </div>`;

const productPage = `<!doctype html>
<html lang="ar" dir="rtl">
  <head><meta charset="utf-8" /></head>
  <body data-template="product_details">
    ${productSection("page-product")}
    <div id="sticky-cta">
      <button type="button" command="show-modal" commandfor="notify-me-dialog">Notify me</button>
    </div>
    <div id="quick-view-content">${productSection("quick-view-product")}</div>
    <dialog id="notify-me-dialog">
      <form data-notify-me-form><input type="hidden" name="product_id" value="" data-notify-product-id /></form>
    </dialog>
  </body>
</html>`;

test.beforeEach(async ({ page }) => {
  await page.route(`${storeOrigin}/**`, (route) => route.fulfill({ contentType: "text/html", body: productPage }));
  await page.goto(`${storeOrigin}/products/p`);
  await page.addScriptTag({ path: themeBundlePath });
});

for (const [name, button, productId] of [
  ["page buy box", "#product-main-section >> nth=0", "page-product"],
  ["sticky bar", "#sticky-cta", "page-product"],
  ["quick view", "#quick-view-content", "quick-view-product"]
]) {
  test(`notify-me dialog targets the ${name} product`, async ({ page }) => {
    await page.locator(button).getByRole("button").click();

    await expect(page.locator("[data-notify-product-id]")).toHaveValue(productId);
  });
}

test("notify-me dialog targets the variant picked inside quick view", async ({ page }) => {
  await page.evaluate(() =>
    window.dispatchEvent(
      new CustomEvent("product:variant-changed", { detail: { selectedProduct: { id: "quick-view-variant" } } })
    )
  );
  await page.locator("#quick-view-content").getByRole("button").click();

  await expect(page.locator("[data-notify-product-id]")).toHaveValue("quick-view-variant");
});
