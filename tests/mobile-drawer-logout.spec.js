import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";

const storeOrigin = "https://store.test";
const drawer = readFileSync(new URL("../components/header/mobile-drawer.jinja", import.meta.url), "utf8");
const loggedInLinks = drawer
  .match(/<div\s+id="mobile-logged-in-links"[\s\S]*?<\/div>/)[0]
  .replace(/\{\{\s*url_for\('profile'\)\s*\}\}/g, "/account")
  .replace(/\{\{\s*_\("([^"]+)"\)\s*\}\}/g, "$1");

test("mobile drawer logout ends the session without the SDK exposing zid.customer", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.addInitScript(() => {
    window.zid = { cart: { get: async () => ({ products: [] }) } };
  });
  await page.route(`${storeOrigin}/**`, (route) =>
    route.fulfill({ contentType: "text/html", body: `<!doctype html><body>${loggedInLinks}</body>` })
  );
  await page.goto(`${storeOrigin}/`);

  await Promise.all([
    page.waitForURL((url) => url.pathname === "/auth/logout", { timeout: 3000 }),
    page.getByText("Log out").click()
  ]);
  expect(errors).toEqual([]);
});
