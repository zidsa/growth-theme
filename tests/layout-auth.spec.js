import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";

const storeOrigin = "https://store.test";
const productPath = "/products/example";
const reviewPath = "/products/example/reviews/new";
const themeBundlePath = fileURLToPath(new URL("../assets/dist/theme.js", import.meta.url));
const cartBundlePath = fileURLToPath(new URL("../assets/dist/cart-controller.js", import.meta.url));

const productPage = `<!doctype html>
<html>
  <head><style>.hidden { display: none !important; }</style></head>
  <body data-template="product_details">
    <button
      type="button"
      data-login-redirect="${storeOrigin}${reviewPath}?source=product#review-form"
      data-auth-guest
    >
      Write a review
    </button>
    <a href="${reviewPath}" class="hidden" data-auth-user>Write a review</a>
  </body>
</html>`;

async function loadTheme(page, { authState } = {}) {
  await page.addInitScript(
    ({ initialAuthState, hasAuthState }) => {
      window.layoutConfig = { profileUrl: "/account" };
      if (hasAuthState) window.customerAuthState = initialAuthState;
      else delete window.customerAuthState;

      // The full theme bundle initializes cart state on every page. Keep that
      // unrelated integration deterministic without exposing zid.customer.
      window.zid = {
        cart: {
          get: async () => ({ products: [] })
        }
      };
    },
    { initialAuthState: authState, hasAuthState: authState !== undefined }
  );
  await page.route(`${storeOrigin}/**`, (route) =>
    route.fulfill({
      contentType: "text/html",
      body: productPage
    })
  );
  await page.goto(`${storeOrigin}${productPath}`);
  await page.addScriptTag({ path: themeBundlePath });
  await expect.poll(() => page.evaluate(() => typeof window.handleLoginAction)).toBe("function");
}

async function expectNavigation(page, action, expectedPath) {
  await Promise.all([page.waitForURL((url) => url.pathname === expectedPath), action()]);
}

test("guest review click preserves the review path when the login popup is unavailable", async ({ page }) => {
  await loadTheme(page, { authState: { isAuthenticated: false, isGuest: true } });

  await expectNavigation(page, () => page.locator("[data-login-redirect]").click(), "/auth/login");

  const loginUrl = new URL(page.url());
  expect(loginUrl.searchParams.get("redirect_to")).toBe(`${reviewPath}?source=product#review-form`);
});

test("authenticated review click navigates to the requested review page", async ({ page }) => {
  await loadTheme(page, { authState: { isAuthenticated: false, isGuest: true } });
  await page.evaluate(() => {
    window.customerAuthState = { isAuthenticated: true, isGuest: false };
  });

  await expectNavigation(page, () => page.locator("[data-login-redirect]").click(), reviewPath);
});

test("customer fetch refreshes cached guest controls for an authenticated shopper", async ({ page }) => {
  await loadTheme(page);
  const guestReviewButton = page.locator("[data-auth-guest]");
  const authenticatedReviewLink = page.locator("[data-auth-user]");

  await expect(guestReviewButton).toBeVisible();
  await expect(authenticatedReviewLink).toBeHidden();

  await page.evaluate(() => {
    document.dispatchEvent(
      new CustomEvent("zid-customer-fetched", {
        detail: { customer: { id: "customer-1", name: "Shopper" } }
      })
    );
  });

  await expect(guestReviewButton).toBeHidden();
  await expect(authenticatedReviewLink).toBeVisible();
  await expectNavigation(page, () => authenticatedReviewLink.click(), reviewPath);
});

test("invalid redirect targets use safe same-origin fallbacks", async ({ page }) => {
  await loadTheme(page, { authState: { isAuthenticated: false, isGuest: true } });
  const guestReviewButton = page.locator("[data-login-redirect]");

  await page.evaluate(() => {
    window.customerAuthState = { isAuthenticated: true, isGuest: false };
    document.querySelector("[data-login-redirect]").dataset.loginRedirect = "https://attacker.test/collect";
  });
  await expectNavigation(page, () => guestReviewButton.click(), "/account");

  await loadTheme(page, { authState: { isAuthenticated: false, isGuest: true } });
  await page.evaluate(() => {
    document.querySelector("[data-login-redirect]").dataset.loginRedirect = "http://[";
  });
  await expectNavigation(page, () => page.locator("[data-login-redirect]").click(), "/auth/login");
  expect(new URL(page.url()).searchParams.get("redirect_to")).toBe("/account");
});

test("login actions without a target retain profile and login defaults", async ({ page }) => {
  await loadTheme(page, { authState: { isAuthenticated: true, isGuest: false } });
  await expectNavigation(page, () => page.evaluate(() => window.handleLoginAction("", false)), "/account");

  await loadTheme(page, { authState: { isAuthenticated: false, isGuest: true } });
  await expectNavigation(page, () => page.evaluate(() => window.handleLoginAction("", false)), "/auth/login");
  expect(new URL(page.url()).searchParams.get("redirect_to")).toBe("/account");
});

test("cart bundle load order keeps the normalized global login handler", async ({ page }) => {
  await loadTheme(page, { authState: { isAuthenticated: false, isGuest: true } });
  await page.addScriptTag({ path: cartBundlePath });
  await page.evaluate(() => {
    window.customerAuthState = { isAuthenticated: true, isGuest: false };
  });

  await expectNavigation(
    page,
    () => page.evaluate(() => window.handleLoginAction("https://attacker.test/collect", false)),
    "/account"
  );
});

test("cart bundle initializes login handling only once", async ({ page }) => {
  await loadTheme(page, { authState: { isAuthenticated: false, isGuest: true } });
  await page.evaluate(() => {
    window.authDialogOpenCount = 0;
    window.auth_dialog = {
      open() {
        window.authDialogOpenCount += 1;
      }
    };
  });
  await page.addScriptTag({ path: cartBundlePath });

  await page.locator("[data-login-redirect]").click();
  await expect.poll(() => page.evaluate(() => window.authDialogOpenCount)).toBe(1);

  await expectNavigation(
    page,
    () => page.evaluate(() => window.dispatchEvent(new CustomEvent("vitrin:auth:success"))),
    reviewPath
  );
});
