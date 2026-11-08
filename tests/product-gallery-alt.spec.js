import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const storeOrigin = "https://store.test";
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));
const photoswipeDir = fileURLToPath(new URL("../node_modules/photoswipe/dist/", import.meta.url));

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

const productName = 'Sample 12" Lamp';
const quotedAlt = 'Box with "quotes" &amp; <tags>';

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

  await page.route("**/*", (route) => route.abort());
  await page.route("https://cdn.jsdelivr.net/npm/photoswipe@5.4.4/dist/*.js", (route) =>
    route.fulfill({
      path: photoswipeDir + new URL(route.request().url()).pathname.split("/").pop(),
      contentType: "text/javascript",
      headers: { "access-control-allow-origin": "*" }
    })
  );
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
    ({ name, media }) =>
      window.productOptionsChanged({
        id: "product-1",
        name,
        sku: "SAMPLE-1",
        in_stock: true,
        is_infinite: true,
        quantity: 10,
        media
      }),
    {
      name: productName,
      media: [
        { id: "1", image: image("front"), alt_text: "Lamp from the front" },
        { id: "2", image: image("side"), alt_text: null },
        { id: "3", image: image("box"), alt_text: quotedAlt },
        { id: "4", image: image("top"), alt_text: "" },
        {
          id: "5",
          image: image("demo"),
          provider: "youtube",
          link: "https://video.test/demo",
          alt_text: "Lamp demo video"
        }
      ]
    }
  );

  const imageAlts = ["Lamp from the front", `${productName} - Image 2`, quotedAlt, `${productName} - Image 4`];
  await expect(page.locator(".product-gallery__slide img")).toHaveCount(5);
  expect(await altsOf(page.locator(".product-gallery__slide img"))).toEqual([...imageAlts, "Lamp demo video"]);
  expect(await altsOf(page.locator("#product-gallery-lightbox img"))).toEqual(imageAlts);

  await expect
    .poll(async () => {
      await page.evaluate(() => window.openImageLightbox(0));
      return page.locator(".pswp-custom-thumb img").count();
    })
    .toBe(4);
  expect(await altsOf(page.locator(".pswp-custom-thumb img"))).toEqual(imageAlts);
});
