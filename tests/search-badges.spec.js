import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const storeOrigin = "https://store.test";
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));

test.beforeEach(async ({ page }) => {
  await page.route(`${storeOrigin}/**`, (route) =>
    route.fulfill({ contentType: "text/html", body: '<!doctype html><html lang="ar"><body></body></html>' })
  );
  await page.goto(`${storeOrigin}/`);
  await page.addScriptTag({ path: themeBundlePath });
});

const badgesFor = (page, product) => page.evaluate((p) => window.searchManager.getProductBadges(p), product);

test("instant search never shows product keywords as badges", async ({ page }) => {
  expect(await badgesFor(page, { keywords: ["مسباح", "سبحة"], price: 149, in_stock: true })).toEqual([]);
});

test("instant search keeps the merchant badge next to keywords", async ({ page }) => {
  const product = { badge: { body: { ar: "حبة واحدة" } }, keywords: ["مسباح", "سبحة"], price: 149, in_stock: true };

  expect(await badgesFor(page, product)).toEqual(["حبة واحدة"]);
});
