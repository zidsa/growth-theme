import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const storeOrigin = "https://store.test";
const productUrl = `${storeOrigin}/products/linen-shirt`;
const variantId = "0b9a4e0c-5d5f-4a52-9a43-2f0f6f0f8a11";
const otherVariantId = "7c1d2b3a-9e8f-4d6c-b5a4-3f2e1d0c9b8a";
const otherProductUrl = `${storeOrigin}/products/cotton-shirt`;
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));

const productPage = `<!doctype html>
<html lang="en" dir="ltr">
  <head><meta charset="utf-8" /></head>
  <body data-template="product_details">
    <div data-product-share="${productUrl}">
      <a id="whatsapp" href="https://api.whatsapp.com/send?text=Check Out this Product: Linen Shirt ${productUrl}">WhatsApp</a>
      <a id="x" href="https://twitter.com/intent/tweet?text=Linen Shirt: ${productUrl}">X</a>
      <a id="facebook" href="https://www.facebook.com/sharer/sharer.php?u=${productUrl}">Facebook</a>
      <button id="copy" type="button" onclick="navigator.clipboard.writeText(productShareUrl('${productUrl}'))">Copy</button>
    </div>
    <div id="quick-view-content">
      <div data-product-share="${otherProductUrl}">
        <a id="quick-view-facebook" href="https://www.facebook.com/sharer/sharer.php?u=${otherProductUrl}">Facebook</a>
        <button id="quick-view-copy" type="button" onclick="navigator.clipboard.writeText(productShareUrl('${otherProductUrl}'))">Copy</button>
      </div>
    </div>
  </body>
</html>`;

async function loadProductPage(page, search = "") {
  await page.addInitScript(() => {
    window.zid = { cart: { get: async () => ({ products: [] }) } };
    window.copied = [];
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: async (text) => window.copied.push(text) }
    });
    document.addEventListener("click", (event) => event.preventDefault());
  });

  await page.route(`${storeOrigin}/**`, (route) => route.fulfill({ contentType: "text/html", body: productPage }));
  await page.goto(`${productUrl}${search}`);
  await page.addScriptTag({ path: themeBundlePath });
  await expect.poll(() => page.evaluate(() => typeof window.productShareUrl)).toBe("function");
}

async function sharedLinks(page) {
  for (const id of ["whatsapp", "x", "facebook", "copy"]) await page.locator(`#${id}`).click();

  return page.evaluate(() => ({
    whatsapp: new URL(document.querySelector("#whatsapp").href).searchParams.get("text"),
    x: new URL(document.querySelector("#x").href).searchParams.get("text"),
    facebook: new URL(document.querySelector("#facebook").href).searchParams.get("u"),
    copy: window.copied.at(-1)
  }));
}

test("share buttons share the plain product link when no variant is in the address", async ({ page }) => {
  await loadProductPage(page);

  expect(await sharedLinks(page)).toEqual({
    whatsapp: `Check Out this Product: Linen Shirt ${productUrl}`,
    x: `Linen Shirt: ${productUrl}`,
    facebook: productUrl,
    copy: productUrl
  });
});

test("share buttons carry the variant in the address and leave other parameters out", async ({ page }) => {
  await loadProductPage(page, `?utm_source=newsletter&pid=${variantId}&gclid=abc`);

  expect(await sharedLinks(page)).toEqual({
    whatsapp: `Check Out this Product: Linen Shirt ${productUrl}?pid=${variantId}`,
    x: `Linen Shirt: ${productUrl}?pid=${variantId}`,
    facebook: `${productUrl}?pid=${variantId}`,
    copy: `${productUrl}?pid=${variantId}`
  });
});

test("share buttons follow the variant as the address changes", async ({ page }) => {
  await loadProductPage(page, `?pid=${variantId}`);
  await sharedLinks(page);

  await page.evaluate((id) => history.replaceState(null, "", `?pid=${id}`), otherVariantId);
  expect((await sharedLinks(page)).facebook).toBe(`${productUrl}?pid=${otherVariantId}`);

  await page.evaluate(() => history.replaceState(null, "", location.pathname));
  expect((await sharedLinks(page)).facebook).toBe(productUrl);
});

test("a quick view of another product shares that product without the variant of the page", async ({ page }) => {
  await loadProductPage(page, `?pid=${variantId}`);

  await page.locator("#quick-view-facebook").click();
  await page.locator("#quick-view-copy").click();

  expect(
    await page.evaluate(() => new URL(document.querySelector("#quick-view-facebook").href).searchParams.get("u"))
  ).toBe(otherProductUrl);
  expect(await page.evaluate(() => window.copied.at(-1))).toBe(otherProductUrl);
});
