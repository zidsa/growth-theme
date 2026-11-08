import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

// INQUIRY-720: the product gallery must not download extra image copies
// (hidden 1600px lightbox images, raw originals after the initial variant
// callback) and must keep each image's own alt when it rebuilds.

const storeOrigin = "https://store.test";
const productPath = "/products/check2";
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));
const cdn = "https://media.zid.store/cdn-cgi/image/";

const media = (n) => ({
  id: `m${n}`,
  image: {
    thumbnail: `https://media.zid.store/store/thumb-${n}.webp`,
    medium: `https://media.zid.store/store/medium-${n}.webp`,
    large: `https://media.zid.store/store/large-${n}.webp`,
    full_size: `https://media.zid.store/store/full-${n}.webp`
  },
  alt_text: `Custom alt ${n}`
});

const initialMedia = [media(1), media(2)];

// Mirrors what components/products/product-gallery.jinja renders on the server.
function serverGallery(items) {
  const slides = items
    .map(
      (item, i) => `
      <div class="product-gallery__slide relative min-w-0 flex-[0_0_100%]">
        <img
          data-media-src="${item.image.large}"
          src="${cdn}w=750,q=90,f=auto/${item.image.large}"
          srcset="${cdn}w=400,q=90,f=auto/${item.image.large} 400w, ${cdn}w=750,q=90,f=auto/${item.image.large} 750w"
          sizes="(max-width: 640px) 100vw, 50vw"
          alt="${item.alt_text}"
          data-lightbox-trigger="${i}"
          ${i === 0 ? 'fetchpriority="high"' : 'loading="lazy"'}
        />
      </div>`
    )
    .join("");
  const lightbox = items
    .map(
      (item) => `<a href="${cdn}w=1600,q=90,f=auto/${item.image.full_size}" data-pswp-width="1600"
        data-pswp-height="2133" data-thumb-src="${cdn}w=160,q=85,f=auto/${item.image.thumbnail}"
        data-alt="${item.alt_text}"></a>`
    )
    .join("");
  const thumbs = items
    .map(
      (item) => `<button class="product-gallery-thumbs__slide" data-gallery-id="product-gallery" type="button">
        <img src="${cdn}w=256,q=85,f=auto/${item.image.thumbnail}" loading="lazy" /></button>`
    )
    .join("");

  return `
    <div id="product-gallery-lightbox" class="hidden">${lightbox}</div>
    <div class="product-gallery" data-gallery-id="product-gallery">
      <div class="product-gallery__container flex">${slides}</div>
    </div>
    <div class="product-gallery-thumbs" data-gallery-id="product-gallery">
      <div class="product-gallery-thumbs__container flex">${thumbs}</div>
    </div>`;
}

// Mirrors components/products/sticky-product-actions.jinja (image only)
const stickyBar = `
  <div id="sticky-cta" class="hidden" data-sticky-cta>
    <img data-media-src="${initialMedia[0].image.thumbnail}"
      src="${cdn}w=128,q=85,f=auto/${initialMedia[0].image.thumbnail}" data-sticky-cta-image />
  </div>`;

const productPage = `<!doctype html>
<html lang="ar" dir="rtl">
  <head><meta charset="utf-8" /></head>
  <body data-template="product_details">${serverGallery(initialMedia)}${stickyBar}</body>
</html>`;

async function loadTheme(page) {
  const imageRequests = [];

  await page.addInitScript(() => {
    window.zid = { cart: { get: async () => ({ products: [] }) } };
  });
  for (const host of ["https://media.zid.store/**", "https://img.zid.store/**"]) {
    await page.route(host, (route) => {
      imageRequests.push(route.request().url());
      route.fulfill({ status: 204 });
    });
  }
  await page.route(`${storeOrigin}/**`, (route) => route.fulfill({ contentType: "text/html", body: productPage }));
  await page.goto(`${storeOrigin}${productPath}`);
  await page.addScriptTag({ path: themeBundlePath });
  await expect.poll(() => page.evaluate(() => typeof window.productOptionsChanged)).toBe("function");

  return imageRequests;
}

test("hidden lightbox markup does not download zoom images", async ({ page }) => {
  const imageRequests = await loadTheme(page);

  await expect(page.locator("#product-gallery-lightbox img")).toHaveCount(0);
  expect(imageRequests.filter((url) => url.includes("w=1600"))).toEqual([]);
});

test("variant callback with the already rendered media keeps the server images", async ({ page }) => {
  const imageRequests = await loadTheme(page);

  await page.evaluate(() => {
    window.__firstSlide = document.querySelector(".product-gallery__container img");
  });

  await page.evaluate(
    (items) => window.productOptionsChanged({ id: "v1", in_stock: true, media: items }),
    initialMedia
  );

  expect(
    await page.evaluate(() => window.__firstSlide === document.querySelector(".product-gallery__container img"))
  ).toBe(true);
  // No raw (non-resized) originals were requested.
  expect(imageRequests.filter((url) => !url.startsWith(cdn))).toEqual([]);
});

test("variant change rebuilds the gallery with the platform URLs, alt text and lazy lightbox data", async ({ page }) => {
  const imageRequests = await loadTheme(page);
  const nextMedia = [media(3), { ...media(4), alt_text: 'Box with "quotes" & <tags>' }];

  await page.evaluate(
    (items) => window.productOptionsChanged({ id: "v2", name: "Check 2", in_stock: true, media: items }),
    nextMedia
  );

  const slides = page.locator(".product-gallery__container img");
  await expect(slides.first()).toHaveAttribute("data-media-src", nextMedia[0].image.large);
  await expect(slides.first()).toHaveAttribute("src", nextMedia[0].image.large);
  await expect(slides.first()).toHaveAttribute("alt", "Custom alt 3");
  await expect(slides.nth(1)).toHaveAttribute("alt", nextMedia[1].alt_text);

  await expect(page.locator(".product-gallery-thumbs__container img").first()).toHaveAttribute(
    "src",
    nextMedia[0].image.thumbnail
  );

  const lightboxLinks = page.locator("#product-gallery-lightbox a");
  await expect(page.locator("#product-gallery-lightbox img")).toHaveCount(0);
  await expect(lightboxLinks.first()).toHaveAttribute("href", nextMedia[0].image.full_size);
  await expect(lightboxLinks.first()).toHaveAttribute("data-alt", "Custom alt 3");
  await expect(lightboxLinks.nth(1)).toHaveAttribute("data-alt", nextMedia[1].alt_text);

  await page.waitForLoadState("networkidle");
  expect(imageRequests.filter((url) => url.includes("full-"))).toEqual([]);
});

test("sticky bar keeps the server image when the variant callback repeats the same media", async ({ page }) => {
  const imageRequests = await loadTheme(page);
  const sticky = page.locator("[data-sticky-cta-image]");
  const serverSrc = await sticky.getAttribute("src");

  await page.evaluate((m) => window.productOptionsChanged({ id: "v1", in_stock: true, media: m }), initialMedia);
  await expect(sticky).toHaveAttribute("src", serverSrc);

  await page.evaluate((m) => window.productOptionsChanged({ id: "v3", in_stock: true, media: m }), [media(3)]);
  await expect(sticky).toHaveAttribute("src", media(3).image.thumbnail);

  await page.waitForLoadState("networkidle");
  expect(imageRequests.filter((url) => url === initialMedia[0].image.thumbnail)).toEqual([]);
});
