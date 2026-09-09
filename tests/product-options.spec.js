import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const storeOrigin = "https://store.test";
const productPath = "/products/revolution-reloaded";
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));

const optionName = "ريفلوشن ريلوديد بودرة اضاءة";
const initialChoice = "دير جست ماي تايب";
const nextChoice = "دير تو ديفولج";

const productOptionsMarkup = `
  <div id="product-variants-options" class="product-options product-options--list">
    <div class="product-options__group" index="0">
      <label class="product-options__label">${optionName}</label>
      <ul name="${optionName}" index="0" class="product-options__list">
        <li
          value="${initialChoice}"
          onclick="productOptionListItemClicked(event)"
          class="product-options__item product-options__item--color active"
        >
          <span class="product-options__swatch"></span>
          <span class="product-options__item-text product-options__item-text--sr">${initialChoice}</span>
        </li>
        <li
          value="${nextChoice}"
          onclick="productOptionListItemClicked(event)"
          class="product-options__item product-options__item--color"
        >
          <span class="product-options__swatch"></span>
          <span class="product-options__item-text product-options__item-text--sr">${nextChoice}</span>
        </li>
      </ul>
    </div>
  </div>`;

const productPage = `<!doctype html>
<html lang="ar" dir="rtl">
  <head><meta charset="utf-8" /></head>
  <body data-template="product_details">${productOptionsMarkup}</body>
</html>`;

const productListingPage = `<!doctype html>
<html lang="ar" dir="rtl">
  <head><meta charset="utf-8" /></head>
  <body data-template="products"></body>
</html>`;

async function loadTheme(page, html = productPage) {
  await page.addInitScript(() => {
    window.zid = {
      cart: {
        get: async () => ({ products: [] })
      }
    };

    window.productOptionListItemClicked = (event) => {
      const selectedOption = event.currentTarget;
      selectedOption.parentElement.querySelectorAll(".product-options__item").forEach((option) => {
        option.classList.toggle("active", option === selectedOption);
      });

      window.productOptionsChanged({
        id: "variant-2",
        sku: "Z.3207461.81659199999999253757",
        in_stock: true,
        is_infinite: true,
        quantity: 100,
        media: []
      });
    };
  });

  await page.route(`${storeOrigin}/**`, (route) =>
    route.fulfill({
      contentType: "text/html",
      body: html
    })
  );
  await page.goto(`${storeOrigin}${productPath}`);
  await page.addScriptTag({ path: themeBundlePath });
  await expect.poll(() => page.evaluate(() => typeof window.productOptionsChanged)).toBe("function");
}

test("color option label shows the active choice on load and after selection", async ({ page }) => {
  await loadTheme(page);

  const optionLabel = page.locator(".product-options__label");
  await expect(optionLabel).toHaveText(`${optionName}: ${initialChoice}`);

  await page.locator(`.product-options__item[value="${nextChoice}"]`).click();

  await expect(optionLabel).toHaveText(`${optionName}: ${nextChoice}`);
});

test("color option label shows the active choice in dynamically loaded product content", async ({ page }) => {
  await loadTheme(page, productListingPage);

  await page.evaluate((markup) => {
    document.body.insertAdjacentHTML("beforeend", markup);
    window.dispatchEvent(new CustomEvent("content:loaded"));
  }, productOptionsMarkup);

  await expect(page.locator(".product-options__label")).toHaveText(`${optionName}: ${initialChoice}`);
});
