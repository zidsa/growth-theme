import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const storeOrigin = "https://store.test";
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));

const productPage = `<!doctype html>
<html lang="en">
  <head><meta charset="utf-8" /></head>
  <body data-template="product_details">
    <div id="product-gallery-lightbox" class="hidden"></div>
    <div class="product-gallery" data-gallery-id="product-gallery">
      <div class="product-gallery__container"></div>
    </div>
    <div class="product-gallery-thumbs hidden" data-gallery-id="product-gallery">
      <div class="product-gallery-thumbs__container"></div>
    </div>
  </body>
</html>`;

const image = (name) => ({
  large: `https://media.test/${name}-large.jpg`,
  full_size: `https://media.test/${name}.jpg`,
  thumbnail: `https://media.test/${name}-thumb.jpg`
});

async function loadTheme(page) {
  await page.addInitScript(() => {
    window.zid = {
      cart: {
        get: async () => ({ products: [] })
      }
    };
  });

  await page.route("https://media.test/**", (route) => route.abort());
  await page.route(`${storeOrigin}/**`, (route) =>
    route.fulfill({
      contentType: "text/html",
      body: productPage
    })
  );
  await page.goto(`${storeOrigin}/products/sample-lamp`);
  await page.addScriptTag({ path: themeBundlePath });
  await expect.poll(() => page.evaluate(() => typeof window.productOptionsChanged)).toBe("function");
}

const altsOf = (locator) => locator.evaluateAll((images) => images.map((img) => img.getAttribute("alt")));

test("gallery rebuilt on product change keeps each image's own alt text", async ({ page }) => {
  await loadTheme(page);

  await page.evaluate(
    (media) =>
      window.productOptionsChanged({
        id: "product-1",
        name: "Sample Lamp",
        sku: "SAMPLE-1",
        in_stock: true,
        is_infinite: true,
        quantity: 10,
        media
      }),
    [
      { id: "1", image: image("front"), alt_text: "Lamp from the front" },
      { id: "2", image: image("side"), alt_text: null },
      { id: "3", image: image("box"), alt_text: 'Box with "quotes" & <tags>' },
      { id: "4", image: image("top"), alt_text: "" },
      {
        id: "5",
        image: image("demo"),
        provider: "youtube",
        link: "https://video.test/demo",
        alt_text: "Lamp demo video"
      }
    ]
  );

  await expect(page.locator(".product-gallery__slide img")).toHaveCount(5);
  expect(await altsOf(page.locator(".product-gallery__slide img"))).toEqual([
    "Lamp from the front",
    "Sample Lamp - Image 2",
    'Box with "quotes" & <tags>',
    "Sample Lamp - Image 4",
    "Lamp demo video"
  ]);
  expect(await altsOf(page.locator("#product-gallery-lightbox img"))).toEqual([
    "Lamp from the front",
    "Sample Lamp - Image 2",
    'Box with "quotes" & <tags>',
    "Sample Lamp - Image 4"
  ]);
});
