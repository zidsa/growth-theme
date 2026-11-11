#!/usr/bin/env node
/**
 * Property checks for the cart group's JavaScript, run against the real modules in
 * assets/js/ with a fake browser (harness/fakedom.mjs). No bundler, no browser.
 *
 * Usage: node js_props.mjs [--root <theme checkout>]
 *   exit 0 = every property matched the outcome recorded in EXPECTED (and in SKILL.md)
 *   exit 1 = a property changed; the line says which and what it saw
 *
 * The recorded outcome is the *interesting* half: a property recorded as "violation"
 * documents a defect the next agent must not "fix" by weakening the property.
 */

import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  El,
  Recorder,
  importPlain,
  installDom,
  loadModule,
  shadowDocument,
} from "./fakedom.mjs";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const rootIndex = argv.indexOf("--root");
const ROOT = path.resolve(rootIndex >= 0 ? argv[rootIndex + 1] : path.join(HERE, "../../../.."));

/** Recorded outcome per property. "holds" | "violation". */
export const EXPECTED = {
  TotalsRows: "holds",
  DiscountSign: "holds",
  TotalsTextEscaping: "violation", // finding: cart strings are interpolated into innerHTML
  ProgressWidth: "violation", // finding: percentage from the API is not clamped
  QuantityBounds: "holds",
  QuantityMirrorsDisplay: "violation", // finding: field/buttons drift from the value
  QuantityTargets: "holds",
  QtyFailureSurfaces: "holds",
  CouponFormState: "holds",
  CouponSubmitOnce: "holds",
  RedemptionRecovers: "holds",
  GiftDeleteRecovers: "holds",
  BadgeConsistency: "holds",
  BadgeOnRefresh: "violation", // finding: badge only refreshes through window.cartManager
  AddToCartBindsOnce: "holds",
  ControllerInitOnce: "holds",
  GiftPopupTimer: "holds",
  RewardsRowsOnce: "holds",
  RefreshFailureFallback: "holds",
};

/** One plain sentence per recorded violation, printed as a FINDING line. */
const FINDINGS = {
  TotalsTextEscaping:
    "totals.js writes coupon code, gift-card code, loyalty label, total title and value into innerHTML unescaped.",
  ProgressWidth:
    "products_subtotal_percentage_from_min is written into the bar width unclamped (202% on store 1's cart).",
  QuantityMirrorsDisplay:
    "qty-input.js leaves the typed text and the delete/minus buttons out of step with the value it reports.",
  BadgeOnRefresh:
    "after a cart re-render the header badge keeps its old count: refresh.js/controller.js only call window.cartManager.",
};

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

// The modules log to console.error exactly on the failure paths this harness drives on
// purpose; keep the output readable. `--verbose` keeps the module logs.
/** The harness's own output; survives the module-log silencing below. */
const report = (line) => process.stdout.write(`${line}\n`);
if (!argv.includes("--verbose")) {
  console.error = () => {};
  console.log = () => {};
}
const text = (html) => html.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();

// ── totals.js ──────────────────────────────────────────────────────────────

const TOTALS_CARTS = () => [
  {
    products_count: 2,
    currency: { cart_currency: { code: "SAR" } },
    totals: [
      { code: "sub_totals", title: "Subtotal", value_string: "198.00 SAR" },
      { code: "products_discount", title: "Discount", value_string: "-22.00 SAR" },
      { code: "vat", title: "VAT", value_string: "26.40 SAR" },
      { code: "total", title: "Total", value_string: "202.40 SAR" },
    ],
  },
  {
    products_count: 1,
    currency: { cart_currency: { code: "SAR" } },
    totals: [
      { code: "sub_totals_before_vat", title: "Subtotal", value_string: "99.00 SAR" },
      { code: "shipping", title: "Shipping", value_string: "15.00 SAR" },
      { code: "total", title: "Total", value_string: "114.00 SAR" },
    ],
  },
  {
    products_count: 3,
    currency: { cart_currency: { code: "SAR" } },
    coupon: { code: "SAVE10" },
    totals: [
      { code: "sub_totals", title: "Subtotal", value_string: "300.00 SAR" },
      { code: "coupon_discount", title: "Discount", value_string: "30.00 SAR" },
      { code: "total", title: "Total", value_string: "270.00 SAR" },
    ],
  },
  {
    products_count: 1,
    currency: { cart_currency: { code: "SAR" } },
    gift_card_details: { code: "GIFT-1", amount_string: "50.00 SAR" },
    loyalty_applied_redemption_method: {
      points_to_redeem: 100,
      reward: { discount_amount: 10 },
    },
    totals: [
      { code: "sub_totals", title: "Subtotal", value_string: "120.00 SAR" },
      { code: "discount", title: "Discount", value_string: "-10.00 SAR" },
      { code: "total", title: "Total", value_string: "60.00 SAR" },
    ],
  },
];

function formatDiscount(value) {
  const str = String(value || "");
  return str.startsWith("-") ? str : "-" + str;
}

async function totalsRows() {
  const sink = new El("div");
  installDom({ query: (s) => (s === "[data-cart-totals]" ? sink : null) });
  const mod = await importPlain("assets/js/cart/totals.js", { root: ROOT });
  const r = new Recorder();

  for (const [i, cart] of TOTALS_CARTS().entries()) {
    sink.innerHTML = "";
    mod.updateCartTotals(cart, { translations: {} });
    const html = sink.innerHTML;
    const total = cart.totals.find((t) => t.code === "total");
    const tag = `case${i}`;

    // Every entry except the total reaches the summary with its own value.
    for (const t of cart.totals) {
      if (t.code === "total") continue;
      const isDiscount = ["discount", "coupon_discount", "products_discount"].includes(t.code);
      const want = isDiscount ? formatDiscount(t.value_string) : t.value_string;
      r.ok(`${tag} ${t.code} present`, html.includes(want), `missing ${JSON.stringify(want)}`);
      if (!isDiscount) {
        r.ok(`${tag} ${t.code} title`, html.includes(t.title), `missing title ${t.title}`);
      }
    }

    // The total row is written last and is the only row in bold.
    const boldCount = (html.match(/font-semibold/g) || []).length;
    r.eq(`${tag} bold cells`, boldCount, 2);
    const lastBold = html.lastIndexOf("font-semibold");
    const firstOther = Math.max(
      ...cart.totals
        .filter((t) => t.code !== "total")
        .map((t) => html.indexOf(isDiscountish(t) ? formatDiscount(t.value_string) : t.value_string))
    );
    r.ok(`${tag} total last`, lastBold > firstOther, `total not after the other rows`);
    r.ok(`${tag} total value`, html.slice(lastBold).includes(total.value_string), "total value missing from the last row");

    // Items count sits on sub_totals only, and carries products_count.
    const itemsCount = `data-cart-items-count`;
    const hasSubTotals = cart.totals.some((t) => t.code === "sub_totals");
    r.eq(`${tag} items-count node`, html.includes(itemsCount), hasSubTotals);
    if (hasSubTotals) {
      r.ok(`${tag} items-count text`, html.includes(`${cart.products_count} items`), "count text missing");
    }

    // Money never carries a doubled sign.
    r.ok(`${tag} no double sign`, !html.includes("--"), "found --");
  }
  return { name: "TotalsRows", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

function isDiscountish(total) {
  return ["discount", "coupon_discount", "products_discount"].includes(total.code);
}

async function discountSign() {
  const sink = new El("div");
  installDom({ query: (s) => (s === "[data-cart-totals]" ? sink : null) });
  const mod = await importPlain("assets/js/cart/totals.js", { root: ROOT });
  const r = new Recorder();

  for (const value of ["-22.00 SAR", "22.00 SAR", "0.00 SAR", "-0.00 SAR", "5", ""]) {
    sink.innerHTML = "";
    mod.updateCartTotals(
      {
        products_count: 1,
        currency: { cart_currency: { code: "SAR" } },
        totals: [
          { code: "sub_totals", title: "Subtotal", value_string: "100.00 SAR" },
          { code: "discount", title: "Discount", value_string: value },
          { code: "total", title: "Total", value_string: "90.00 SAR" },
        ],
      },
      { translations: {} }
    );
    const html = sink.innerHTML;
    const cells = [...html.matchAll(/text-success text-sm shrink-0 text-end">([^<]*)</g)].map((m) => m[1]);
    r.eq(`discount ${JSON.stringify(value)} cells`, cells, [formatDiscount(value)]);
    r.ok(`discount ${JSON.stringify(value)} one sign`, !html.includes("--"), "found --");
  }
  return { name: "DiscountSign", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

async function totalsTextEscaping() {
  const sink = new El("div");
  installDom({ query: (s) => (s === "[data-cart-totals]" ? sink : null) });
  const mod = await importPlain("assets/js/cart/totals.js", { root: ROOT });
  const r = new Recorder();
  const payload = `<img src=x onerror="window.__pwned=1">`;
  const base = { products_count: 1, currency: { cart_currency: { code: "SAR" } } };

  const cases = {
    coupon: { ...base, coupon: { code: payload }, totals: [
      { code: "sub_totals", title: "Sub", value_string: "1.00 SAR" },
      { code: "coupon_discount", title: "Discount", value_string: "-1.00 SAR" },
      { code: "total", title: "Total", value_string: "0.00 SAR" },
    ] },
    giftCard: { ...base, gift_card_details: { code: payload }, totals: [
      { code: "sub_totals", title: "Sub", value_string: "1.00 SAR" },
      { code: "discount", title: "Discount", value_string: "-1.00 SAR" },
      { code: "total", title: "Total", value_string: "0.00 SAR" },
    ] },
    title: { ...base, totals: [
      { code: "sub_totals", title: payload, value_string: "1.00 SAR" },
      { code: "total", title: "Total", value_string: "1.00 SAR" },
    ] },
    value: { ...base, totals: [
      { code: "sub_totals", title: "Sub", value_string: "1.00 SAR" },
      { code: "total", title: "Total", value_string: payload },
    ] },
    loyalty: { ...base, loyalty_applied_redemption_method: { points_to_redeem: payload, reward: { discount_amount: 1 } }, totals: [
      { code: "sub_totals", title: "Sub", value_string: "1.00 SAR" },
      { code: "discount", title: "Discount", value_string: "-1.00 SAR" },
      { code: "total", title: "Total", value_string: "0.00 SAR" },
    ] },
  };

  for (const [name, cart] of Object.entries(cases)) {
    sink.innerHTML = "";
    mod.updateCartTotals(cart, { translations: {} });
    const html = sink.innerHTML;
    r.ok(`${name} escapes markup`, !html.includes(payload), `${name} inserted the payload as markup`);
  }
  return { name: "TotalsTextEscaping", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

async function progressWidth() {
  const section = new El("div");
  const message = new El("p");
  const bar = new El("div");
  const wrapper = new El("div");
  const percentText = new El("span");
  const success = new El("div");
  installDom({
    query: (s) =>
      ({
        "[data-free-shipping-bar]": section,
        "[data-free-shipping-message]": message,
        "[data-free-shipping-progress-bar]": bar,
        "[data-free-shipping-progress-wrapper]": wrapper,
        "[data-free-shipping-percentage]": percentText,
        "[data-free-shipping-success]": success,
      })[s] ?? null,
  });
  const mod = await importPlain("assets/js/cart/totals.js", { root: ROOT });
  const r = new Recorder();

  for (const pct of [0, 12, 99, 100, 101, 202, 350]) {
    bar.style = {};
    percentText.textContent = "";
    mod.updateFreeShippingProgress(
      {
        free_shipping_rule: {
          subtotal_condition: {
            status: "min_not_reached",
            products_subtotal_percentage_from_min: pct,
            remaining: "10.00 SAR",
          },
        },
      },
      {}
    );
    const width = bar.style.width;
    const value = parseFloat(width);
    r.ok(`pct ${pct} numeric width`, Number.isFinite(value), `width is ${JSON.stringify(width)}`);
    r.ok(`pct ${pct} within track`, value >= 0 && value <= 100, `width ${width} is outside 0-100%`);
    if (percentText.textContent) {
      r.ok(`pct ${pct} label within track`, parseFloat(percentText.textContent) <= 100, `label ${percentText.textContent}`);
    }
  }
  return { name: "ProgressWidth", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

// ── features/qty-input.js ──────────────────────────────────────────────────

function makeQty({ id, value = 1, min = "1", max = "", showDelete = true }) {
  const wrapper = new El("div");
  wrapper.dataset.qtyInput = id;
  wrapper.value = value;
  const input = new El("input", { value: String(value), min: String(min), max: String(max) });
  const buttons = {
    increase: new El("button"),
    decrease: new El("button"),
    remove: new El("button"),
  };
  buttons.increase.dataset.qtyAction = "increase";
  buttons.decrease.dataset.qtyAction = "decrease";
  buttons.remove.dataset.qtyAction = "remove";
  if (!showDelete) buttons.remove = null;
  const list = Object.values(buttons).filter(Boolean);
  wrapper._sel = (sel) => {
    if (sel === "[data-qty-value]") return input;
    const m = /\[data-qty-action="(\w+)"\]/.exec(sel);
    if (m) return buttons[m[1]] || null;
    return null;
  };
  wrapper._selAll = (sel) => (sel === "[data-qty-action]" ? list : []);
  wrapper.input = input;
  wrapper.buttons = buttons;
  const seen = [];
  wrapper.addEventListener("qty:change", (e) => seen.push(e.detail.value));
  wrapper.seen = seen;
  return wrapper;
}

async function quantityBounds() {
  const alphabet = ["inc", "dec", "type:0", "type:7", "type:99", "clear"];
  const ranges = [
    { min: "1", max: "" },
    { min: "1", max: "5" },
    { min: "2", max: "10" },
  ];
  const r = new Recorder();

  for (const range of ranges) {
    for (const seq of sequences(alphabet, 3)) {
      const wrappers = [makeQty({ id: `qty-${range.min}-${range.max}`, ...range, value: Number(range.min) })];
      installDom({
        query: (sel) => {
          const m = /^\[data-qty-input="(.+)"\]$/.exec(sel);
          return m ? wrappers.find((w) => w.dataset.qtyInput === m[1]) || null : null;
        },
        queryAll: (sel) => (sel === "[data-qty-input]" ? wrappers : []),
      });
      const mod = await loadModule("assets/js/features/qty-input.js", { root: ROOT, expose: ["initAll"] });
      mod.initAll();
      const w = wrappers[0];
      const label = `min${range.min}/max${range.max || "inf"} ${seq.join(",")}`;
      const floor = Math.max(1, Number(range.min));
      const ceil = range.max ? Number(range.max) : Infinity;

      for (const action of seq) {
        if (action === "inc") w.buttons.increase.dispatchEvent(new Event("click"));
        else if (action === "dec") w.buttons.decrease.dispatchEvent(new Event("click"));
        else if (action === "clear") {
          w.input.value = "";
          w.input.dispatchEvent(new Event("input"));
        } else {
          w.input.value = action.split(":")[1];
          w.input.dispatchEvent(new Event("input"));
        }
        // The value the component reports is always a usable quantity.
        if (!w.seen.length) continue;
        const reported = w.seen[w.seen.length - 1];
        if (!r.ok(`${label} reports a number`, Number.isFinite(reported), `reported ${reported}`)) continue;
        r.ok(`${label} reports >= ${floor}`, reported >= floor, `reported ${reported} below ${floor}`);
        r.ok(`${label} reports <= ${ceil}`, reported <= ceil, `reported ${reported} above ${ceil}`);
      }
      if (r.failures.length > 4) break;
    }
  }
  return { name: "QuantityBounds", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

async function quantityMirrorsDisplay() {
  const alphabet = ["inc", "dec", "type:0", "type:7", "clear"];
  const ranges = [{ min: "1", max: "" }, { min: "1", max: "5" }];
  const r = new Recorder();

  for (const range of ranges) {
    for (const seq of sequences(alphabet, 2)) {
      const wrappers = [makeQty({ id: `qty-${range.min}-${range.max}`, ...range, value: Number(range.min) })];
      installDom({
        query: (sel) => {
          const m = /^\[data-qty-input="(.+)"\]$/.exec(sel);
          return m ? wrappers.find((w) => w.dataset.qtyInput === m[1]) || null : null;
        },
        queryAll: (sel) => (sel === "[data-qty-input]" ? wrappers : []),
      });
      const mod = await loadModule("assets/js/features/qty-input.js", { root: ROOT, expose: ["initAll"] });
      mod.initAll();
      const w = wrappers[0];
      const label = `min${range.min}/max${range.max || "inf"} ${seq.join(",")}`;

      for (const action of seq) {
        if (action === "inc") w.buttons.increase.dispatchEvent(new Event("click"));
        else if (action === "dec") w.buttons.decrease.dispatchEvent(new Event("click"));
        else if (action === "clear") {
          w.input.value = "";
          w.input.dispatchEvent(new Event("input"));
        } else {
          w.input.value = action.split(":")[1];
          w.input.dispatchEvent(new Event("input"));
        }
        const shown = w.input.value;
        const reported = w.seen[w.seen.length - 1];
        r.eq(`${label} field shows the reported value`, shown, String(reported));
        if (w.buttons.decrease && w.buttons.remove) {
          r.eq(`${label} delete shown only at 1`, w.buttons.remove.hidden, Number(shown) > 1);
          r.eq(`${label} minus shown above 1`, w.buttons.decrease.hidden, Number(shown) <= 1);
        }
      }
      if (r.failures.length > 4) break;
    }
  }
  return { name: "QuantityMirrorsDisplay", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

function* sequences(alphabet, maxLen) {
  yield [];
  for (let len = 1; len <= maxLen; len += 1) {
    const idx = new Array(len).fill(0);
    while (true) {
      yield idx.map((i) => alphabet[i]);
      let pos = len - 1;
      while (pos >= 0 && idx[pos] === alphabet.length - 1) {
        idx[pos] = 0;
        pos -= 1;
      }
      if (pos < 0) break;
      idx[pos] += 1;
    }
  }
}

// ── cart/quantity.js ───────────────────────────────────────────────────────

async function quantityTargets() {
  const { doc, win } = installDom({});
  const mod = await loadModule("assets/js/cart/quantity.js", {
    root: ROOT,
    expose: ["setupQuantityInputHandlers", "handleCartQuantityChange", "handleCartProductRemove"],
  });
  const r = new Recorder();
  const changes = [];
  const removes = [];
  mod.setupQuantityInputHandlers((...a) => changes.push(a), (...a) => removes.push(a));

  const wrapper = new El("div", { dataset: { cartProductId: "cart-line-9", productId: "catalog-9" } });
  const fakeTarget = { closest: () => wrapper };
  const changeHandler = doc.listeners("qty:change")[0];
  const removeHandler = doc.listeners("qty:remove")[0];
  r.ok("qty:change listener registered", typeof changeHandler === "function", "no document listener");
  r.ok("qty:remove listener registered", typeof removeHandler === "function", "no document listener");

  changeHandler({ target: fakeTarget, detail: { value: 3 } });
  r.eq("qty:change uses the cart line id first", changes, [["cart-line-9", "catalog-9", 3]]);
  removeHandler({ target: fakeTarget });
  r.eq("qty:remove uses the cart line id first", removes, [["cart-line-9", "catalog-9"]]);

  // A wrapper without a cart id belongs to a product card, not the cart page.
  const card = new El("div", { dataset: { productId: "catalog-9" } });
  changes.length = 0;
  changeHandler({ target: { closest: () => card }, detail: { value: 2 } });
  r.eq("product-card quantity ignored", changes, []);

  // The SDK call carries the cart line id, not the catalog id.
  const calls = [];
  const events = [];
  win.addEventListener("zidcart:loading", (e) => events.push(["loading", e.detail]));
  win.addEventListener("zidcart:error", (e) => events.push(["error", e.detail]));
  win.zid = {
    cart: {
      updateProduct: (payload) => {
        calls.push(payload);
        return Promise.resolve({ ok: true });
      },
      removeProduct: (payload) => {
        calls.push(payload);
        return Promise.resolve({ ok: true });
      },
    },
  };
  await mod.handleCartQuantityChange("cart-line-9", "catalog-9", 4);
  r.eq("updateProduct payload", calls[0], { product_id: "cart-line-9", quantity: 4 });
  r.eq("loading before update", events[0] && events[0][0], "loading");
  r.eq("no error on success", events.filter((e) => e[0] === "error"), []);

  calls.length = 0;
  await mod.handleCartProductRemove("cart-line-9", "catalog-9");
  r.eq("removeProduct payload", calls[0], { product_id: "cart-line-9" });

  return { name: "QuantityTargets", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

async function qtyFailureSurfaces() {
  const { win } = installDom({});
  const mod = await loadModule("assets/js/cart/quantity.js", {
    root: ROOT,
    expose: ["handleCartQuantityChange", "handleCartProductRemove"],
  });
  const r = new Recorder();
  const events = [];
  win.addEventListener("zidcart:loading", (e) => events.push(["loading", e.detail]));
  win.addEventListener("zidcart:error", (e) => events.push(["error", e.detail]));

  let success = 0;
  win.zid = {
    cart: {
      updateProduct: () => Promise.reject(new Error("boom")),
      removeProduct: () => Promise.reject(new Error("boom")),
    },
  };
  await mod.handleCartQuantityChange("line-1", "prod-1", 2, () => (success += 1));
  await settle();
  const errors = events.filter((e) => e[0] === "error");
  r.eq("update rejection reports an error", errors.length, 1);
  r.eq("update error operation", errors[0] && errors[0][1].operation, "update");
  r.eq("update rejection runs no success callback", success, 0);

  events.length = 0;
  await mod.handleCartProductRemove("line-1", "prod-1", () => (success += 1));
  await settle();
  const removeErrors = events.filter((e) => e[0] === "error");
  r.eq("remove rejection reports an error", removeErrors.length, 1);
  r.eq("remove error operation", removeErrors[0] && removeErrors[0][1].operation, "remove");
  r.eq("remove rejection runs no success callback", success, 0);

  return { name: "QtyFailureSurfaces", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

// ── cart/coupon.js ─────────────────────────────────────────────────────────

function couponDom() {
  const input = new El("input");
  const btn = new El("button", { disabled: true });
  const text = new El("span");
  const spinner = new El("svg", { className: "" });
  spinner.classList.add("hidden");
  const deleteBtn = new El("button");
  const deleteIcon = new El("svg");
  const deleteSpinner = new El("svg");
  deleteSpinner.classList.add("hidden");
  const map = {
    "[data-coupon-input]": input,
    "[data-coupon-submit-btn]": btn,
    "[data-coupon-submit-text]": text,
    "[data-coupon-submit-spinner]": spinner,
    "[data-coupon-delete-btn]": deleteBtn,
    "[data-coupon-delete-icon]": deleteIcon,
    "[data-coupon-delete-spinner]": deleteSpinner,
  };
  installDom({ query: (s) => map[s] ?? null });
  return { input, btn, text, spinner, deleteBtn, deleteIcon, deleteSpinner };
}

async function couponFormState() {
  const dom = couponDom();
  const mod = await loadModule("assets/js/cart/coupon.js", {
    root: ROOT,
    expose: ["setupCouponInput", "applyCoupon"],
  });
  const r = new Recorder();
  mod.setupCouponInput();

  for (const value of ["", " ", "   ", "\t", "A", "  AB  ", "AB C"]) {
    dom.input.value = value;
    dom.input.dispatchEvent(new Event("input"));
    r.eq(`button disabled for ${JSON.stringify(value)}`, dom.btn.disabled, !value.trim());
  }

  const calls = [];
  window.zid = { cart: { applyCoupon: (payload) => (calls.push(payload), Promise.resolve()) } };
  dom.btn.disabled = true;
  dom.input.value = "ABC";
  await mod.applyCoupon();
  r.eq("disabled button sends nothing", calls, []);

  return { name: "CouponFormState", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

async function couponSubmitOnce() {
  const dom = couponDom();
  const mod = await loadModule("assets/js/cart/coupon.js", {
    root: ROOT,
    expose: ["applyCoupon", "removeCoupon", "setupCouponInput"],
  });
  const r = new Recorder();
  const calls = [];
  let succeed = true;
  let onSuccessCount = 0;
  window.zid = {
    cart: {
      applyCoupon: (payload) => {
        calls.push(payload);
        return succeed ? Promise.resolve({ ok: true }) : Promise.reject(new Error("rejected"));
      },
      removeCoupons: () => (succeed ? Promise.resolve({ ok: true }) : Promise.reject(new Error("nope"))),
    },
  };

  dom.btn.disabled = false;
  dom.input.value = "  SAVE10  ";
  const inflight = mod.applyCoupon(() => (onSuccessCount += 1));
  r.eq("one request per submit", calls, [{ coupon_code: "SAVE10" }]);
  r.eq("busy disables the button", dom.btn.disabled, true);
  r.eq("busy hides the label", dom.text.classList.contains("hidden"), true);
  r.eq("busy shows the spinner", dom.spinner.classList.contains("hidden"), false);
  calls.length = 0;
  await mod.applyCoupon(() => (onSuccessCount += 1)); // a second click while busy
  r.eq("busy submit sends nothing", calls, []);
  await inflight;
  r.eq("success runs the refresh callback once", onSuccessCount, 1);

  // A rejected code must hand the control back.
  dom.btn.disabled = false;
  dom.spinner.classList.add("hidden");
  succeed = false;
  await mod.applyCoupon(() => (onSuccessCount += 1));
  await settle();
  r.eq("rejected submit re-enables", dom.btn.disabled, false);
  r.eq("rejected submit hides the spinner", dom.spinner.classList.contains("hidden"), true);
  r.eq("rejected submit restores the label", dom.text.classList.contains("hidden"), false);
  r.eq("rejected submit refocuses the input", dom.input.focused, 1);
  r.eq("rejected submit runs no callback", onSuccessCount, 1);

  // Remove: same busy/restore discipline, with the icon instead of the label.
  succeed = false;
  dom.deleteBtn.disabled = false;
  dom.deleteIcon.classList.remove("hidden");
  await mod.removeCoupon(() => (onSuccessCount += 1));
  await settle();
  r.eq("rejected remove restores the icon", dom.deleteIcon.classList.contains("hidden"), false);
  r.eq("rejected remove hides the spinner", dom.deleteSpinner.classList.contains("hidden"), true);
  r.eq("rejected remove runs no callback", onSuccessCount, 1);

  return { name: "CouponSubmitOnce", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

// ── cart/loyalty.js ────────────────────────────────────────────────────────

async function redemptionRecovers() {
  const select = new El("el-select", { value: "m1" });
  const applyBtn = new El("button");
  const applyText = new El("span");
  const applySpinner = new El("svg");
  applySpinner.classList.add("hidden");
  const removeBtn = new El("button");
  const removeIcon = new El("svg");
  const removeSpinner = new El("svg");
  removeSpinner.classList.add("hidden");
  const map = {
    "[data-loyalty-redemption-select]": select,
    "[data-loyalty-apply-btn]": applyBtn,
    "[data-loyalty-apply-text]": applyText,
    "[data-loyalty-apply-spinner]": applySpinner,
    "[data-loyalty-remove-btn]": removeBtn,
    "[data-loyalty-remove-icon]": removeIcon,
    "[data-loyalty-remove-spinner]": removeSpinner,
  };
  installDom({ query: (s) => map[s] ?? null });
  const mod = await loadModule("assets/js/cart/loyalty.js", {
    root: ROOT,
    stub: "const initAuthVisibility = () => {};",
    expose: ["applyLoyaltyRedemption", "removeLoyaltyRedemption"],
  });
  const r = new Recorder();
  let success = 0;
  let mode = "reject";
  window.zid = {
    cart: {
      addRedemptionMethod: () =>
        mode === "reject" ? Promise.reject(new Error("no")) : Promise.resolve({ ok: mode === "ok" }),
      removeRedemptionMethod: () =>
        mode === "reject" ? Promise.reject(new Error("no")) : Promise.resolve({ ok: mode === "ok" }),
    },
  };

  // Rejected apply restores the control.
  await mod.applyLoyaltyRedemption(() => (success += 1));
  await settle();
  r.eq("rejected apply re-enables", applyBtn.disabled, false);
  r.eq("rejected apply hides spinner", applySpinner.classList.contains("hidden"), true);
  r.eq("rejected apply restores label", applyText.classList.contains("hidden"), false);
  r.eq("rejected apply runs no callback", success, 0);

  // ok:false is a failure too.
  mode = "false";
  applyBtn.disabled = false;
  applyText.classList.remove("hidden");
  applySpinner.classList.add("hidden");
  await mod.applyLoyaltyRedemption(() => (success += 1));
  await settle();
  r.eq("ok:false apply re-enables", applyBtn.disabled, false);
  r.eq("ok:false apply runs no callback", success, 0);

  // A successful apply hands over to the page refresh (button stays busy by design).
  mode = "ok";
  applyBtn.disabled = false;
  await mod.applyLoyaltyRedemption(() => (success += 1));
  await settle();
  r.eq("successful apply runs the refresh callback", success, 1);
  r.eq("successful apply keeps the button busy until the swap", applyBtn.disabled, true);

  // Remove: failure restores the icon.
  mode = "reject";
  removeIcon.classList.remove("hidden");
  await mod.removeLoyaltyRedemption(() => (success += 1));
  await settle();
  r.eq("rejected remove restores icon", removeIcon.classList.contains("hidden"), false);
  r.eq("rejected remove hides spinner", removeSpinner.classList.contains("hidden"), true);
  r.eq("rejected remove runs no callback", success, 1);

  // An empty select never calls the SDK.
  select.value = "";
  let called = false;
  window.zid.cart.addRedemptionMethod = () => {
    called = true;
    return Promise.resolve({ ok: true });
  };
  applyBtn.disabled = false;
  await mod.applyLoyaltyRedemption(() => (success += 1));
  r.eq("no selection sends nothing", called, false);

  return { name: "RedemptionRecovers", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

// ── cart/gift.js ───────────────────────────────────────────────────────────

async function giftDeleteRecovers() {
  const icon = new El("svg");
  const spinner = new El("svg");
  spinner.classList.add("hidden");
  installDom({
    query: (s) =>
      ({ "[data-gift-delete-icon]": icon, "[data-gift-delete-spinner]": spinner })[s] ?? null,
  });
  const mod = await loadModule("assets/js/cart/gift.js", {
    root: ROOT,
    stub: "const refreshCartPage = () => { window.__refreshed = (window.__refreshed || 0) + 1; };",
    expose: ["deleteGiftCard"],
  });
  const r = new Recorder();

  window.zid = { cart: { removeGiftCard: () => Promise.reject(new Error("no")) } };
  await mod.deleteGiftCard();
  await settle();
  r.eq("failed delete restores the icon", icon.classList.contains("hidden"), false);
  r.eq("failed delete hides the spinner", spinner.classList.contains("hidden"), true);
  r.eq("failed delete does not reload", window.__reloads || 0, 0);

  window.zid.cart.removeGiftCard = () => Promise.resolve({ ok: true });
  await mod.deleteGiftCard();
  await settle();
  r.eq("successful delete reloads once", window.__reloads, 1);

  return { name: "GiftDeleteRecovers", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

// ── cart/badge.js ──────────────────────────────────────────────────────────

function badges(count = 2) {
  return Array.from({ length: count }, () => new El("span", { textContent: "0", hidden: true }));
}

async function badgeConsistency() {
  const r = new Recorder();
  const cases = [
    [{ cart_items_quantity: 4, products_count: 2 }, "4"],
    [{ products_count: 2 }, "2"],
    [{ cart_items_quantity: 0, products_count: 0 }, "0"],
    [{}, "0"],
  ];
  for (const [cart, want] of cases) {
    const els = badges(2);
    installDom({ queryAll: (s) => (s === "[data-cart-badge]" ? els : []) });
    const mod = await importPlain("assets/js/cart/badge.js", { root: ROOT });
    window.zid = { cart: { get: () => Promise.resolve(cart) } };
    await mod.refreshBadge();
    r.eq(`badge ${JSON.stringify(cart)} text`, els.map((e) => e.textContent), [want, want]);
    r.eq(`badge ${JSON.stringify(cart)} hidden`, els.map((e) => e.hidden), [want === "0", want === "0"]);
  }

  // A failed cart read leaves the badges alone instead of blanking them.
  const els = badges(1);
  els[0].textContent = "7";
  els[0].hidden = false;
  installDom({ queryAll: (s) => (s === "[data-cart-badge]" ? els : []) });
  const mod = await importPlain("assets/js/cart/badge.js", { root: ROOT });
  window.zid = { cart: { get: () => Promise.reject(new Error("offline")) } };
  await mod.refreshBadge();
  r.eq("failed read keeps the badge", [els[0].textContent, els[0].hidden], ["7", false]);

  return { name: "BadgeConsistency", holds: r.failures.length === 0, detail: r.failures.slice(0, 4) };
}

// ── refresh.js + controller.js: the badge must follow the re-render ────────

function refreshDom({ badgeText = "2" } = {}) {
  const badge = new El("span", { textContent: badgeText });
  const productsList = new El("div");
  const totals = new El("div");
  const coupon = new El("div");
  const loyalty = new El("div");
  const shipping = new El("div");
  const widgets = new El("div");
  const cart = new El("div");
  const map = {
    "[data-cart-products-list]": productsList,
    "[data-cart-totals]": totals,
    "[data-coupon-section]": coupon,
    "[data-loyalty-section]": loyalty,
    "[data-free-shipping-bar]": shipping,
    "[data-payment-widgets]": widgets,
    ".cart-with-products": cart,
    ".theme-container": new El("div"),
    "[data-cart-badge]": badge,
  };
  installDom({ query: (s) => map[s] ?? null });
  return { badge, map };
}

async function badgeOnRefresh() {
  const r = new Recorder();

  // refreshCartPage: the fetched page's badge says 1, the live page still says 2.
  refreshDom({ badgeText: "2" });
  const fetched = shadowDocument({
    ".cart-with-products": new El("div"),
    "[data-cart-products-list]": new El("div", { innerHTML: "<div>x</div>" }),
    "[data-cart-totals]": new El("div", { innerHTML: "<div>10.00</div>" }),
    "[data-coupon-section]": new El("div", { innerHTML: "" }),
    "[data-loyalty-section]": new El("div", { innerHTML: "" }),
    "[data-free-shipping-bar]": new El("div", { innerHTML: "" }),
    "[data-payment-widgets]": new El("div", { innerHTML: "" }),
    "[data-cart-badge]": new El("span", { textContent: "1" }),
  });
  globalThis.DOMParser = class {
    parseFromString() {
      return fetched;
    }
  };
  globalThis.fetch = () => Promise.resolve({ ok: true, text: () => Promise.resolve("<html></html>") });
  const refresh = await loadModule("assets/js/cart/refresh.js", {
    root: ROOT,
    stub: [
      "const updatePaymentWidgets = () => {};",
      "const updateLoyaltyDisplay = () => {};",
      "const setupCouponInput = () => {};",
      "const initAuthVisibility = () => {};",
    ].join("\n"),
    expose: ["refreshCartPage"],
  });
  await refresh.refreshCartPage();
  const badge = document.querySelector("[data-cart-badge]");
  r.eq("refreshCartPage leaves the badge at the fetched count", badge.textContent, "1");

  // cartProductsHtmlChanged: same gap on the platform-callback path.
  const dom = refreshDom({ badgeText: "2" });
  const controller = await loadController();
  controller.cartProductsHtmlChanged("<div>line</div>", {
    products_count: 1,
    totals: [{ code: "total", title: "Total", value_string: "10.00 SAR" }],
  });
  r.eq("cartProductsHtmlChanged leaves the badge at products_count", dom.badge.textContent, "1");

  return { name: "BadgeOnRefresh", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

// ── controller.js ──────────────────────────────────────────────────────────

const CONTROLLER_STUB = [
  "const __calls = (window.__stubCalls = window.__stubCalls || []);",
  "const rec = (name) => (...args) => { __calls.push([name, args]); };",
  "const setupCouponInput = rec('setupCouponInput');",
  "const applyCoupon = rec('applyCoupon');",
  "const removeCoupon = rec('removeCoupon');",
  "const initLoyaltyProgram = rec('initLoyaltyProgram');",
  "const calculateLoyaltyPoints = rec('calculateLoyaltyPoints');",
  "const applyLoyaltyRedemption = rec('applyLoyaltyRedemption');",
  "const removeLoyaltyRedemption = rec('removeLoyaltyRedemption');",
  "const handleGiftCardClick = rec('handleGiftCardClick');",
  "const editGiftCard = rec('editGiftCard');",
  "const deleteGiftCard = rec('deleteGiftCard');",
  "const updateGiftCardDisplay = rec('updateGiftCardDisplay');",
  "const setupGiftEventListener = rec('setupGiftEventListener');",
  "const updateCartTotals = rec('updateCartTotals');",
  "const updateFreeShippingProgress = rec('updateFreeShippingProgress');",
  "const setupQuantityInputHandlers = rec('setupQuantityInputHandlers');",
  "const updateQuantity = rec('updateQuantity');",
  "const refreshCartPage = rec('refreshCartPage');",
  "const setCartLoadingState = rec('setCartLoadingState');",
  "const setupZidCartEventListeners = rec('setupZidCartEventListeners');",
  "const handleLoginAction = rec('handleLoginAction');",
].join("\n");

async function loadController() {
  return loadModule("assets/js/cart/controller.js", {
    root: ROOT,
    stub: CONTROLLER_STUB,
    expose: ["init", "state", "cartProductsHtmlChanged"],
  });
}

async function controllerInitOnce() {
  const { doc } = installDom({ query: () => null });
  const mod = await loadController();
  const r = new Recorder();
  window.__stubCalls.length = 0;

  mod.init({ cart: { products_count: 1 }, loyaltyEnabled: false, translations: {} });
  mod.init({ cart: { products_count: 1 }, loyaltyEnabled: false, translations: {} });
  r.eq("init sets the initialized flag", mod.state.isInitialized, true);
  r.eq("one submit delegation after two inits", doc.listeners("submit").length, 1);

  const form = new El("form", { dataset: { couponForm: "" } });
  const event = { target: { closest: () => form }, preventDefault() {} };
  for (const listener of doc.listeners("submit")) listener(event);
  const applies = window.__stubCalls.filter(([name]) => name === "applyCoupon");
  r.eq("one submit applies one coupon", applies.length, 1);
  r.eq("public API exposed", typeof window.CartPage.init, "function");

  return { name: "ControllerInitOnce", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

// ── add-to-cart.js ─────────────────────────────────────────────────────────

async function addToCartBindsOnce() {
  const btn = new El("button", { dataset: { addToCart: "prod-1" }, disabled: false });
  const calls = [];
  installDom({
    queryAll: (s) =>
      ({
        "[data-add-to-cart]": [btn],
        "[data-add-to-cart-form]": [],
        "[data-buy-now-form]": [],
        "[data-add-variant-to-cart]": [],
        "[data-open-quick-view]": [],
        "[data-qty-input]": [],
        "[data-product-card]": [],
      })[s] ?? [],
  });
  const mod = await loadModule("assets/js/cart/add-to-cart.js", {
    root: ROOT,
    stub: [
      "const showSpinner = () => {};",
      "const hideSpinner = () => {};",
      "const dispatch = () => {};",
      "const requestRequiredCustomerLocation = () => {};",
      "const refreshBadge = () => {};",
    ].join("\n"),
    expose: ["initButtons"],
  });
  const r = new Recorder();
  window.zid = { cart: { addProduct: (payload) => (calls.push(payload), Promise.resolve({ ok: true })) } };

  mod.initButtons();
  mod.initButtons();
  btn.dispatchEvent(new Event("click"));
  await settle();
  r.eq("one click adds once", calls, [{ product_id: "prod-1", quantity: 1 }]);

  btn.disabled = true;
  btn.dispatchEvent(new Event("click"));
  await settle();
  r.eq("disabled button adds nothing", calls.length, 1);

  return { name: "AddToCartBindsOnce", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

// ── features/gifting.js ────────────────────────────────────────────────────

async function giftPopupTimer() {
  const popup = new El("div", { hidden: true });
  const close = new El("button");
  installDom({
    query: (s) => ({ "[data-gift-cart-popup]": popup, "[data-gift-popup-close]": close })[s] ?? null,
  });
  await loadModule("assets/js/features/gifting.js", { root: ROOT });
  const r = new Recorder();
  const add = () => window.dispatchEvent(new CustomEvent("cart:updated", { detail: { action: "add" } }));

  // An add shows the hint and starts exactly one hide timer.
  add();
  r.eq("popup shown after an add", popup.hidden, false);
  r.eq("one pending hide timer", activeTimers(), 1);

  // A second add keeps it shown and does not stack timers.
  add();
  r.eq("second add keeps it shown", popup.hidden, false);
  r.eq("second add still one timer", activeTimers(), 1);

  // The close button hides it now and cancels the pending hide.
  close.dispatchEvent(new Event("click"));
  r.eq("close hides the popup", popup.hidden, true);
  r.eq("close cancels the hide timer", activeTimers(), 0);

  // Left alone, the hint hides itself ~4 s after the last add.
  add();
  await new Promise((resolve) => setTimeout(resolve, 4300));
  r.eq("popup hides after the delay", popup.hidden, true);

  return { name: "GiftPopupTimer", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

function activeTimers() {
  return typeof process._getActiveHandles === "function"
    ? process.getActiveResourcesInfo().filter((t) => t === "Timeout").length
    : 1;
}

// ── features/loyalty-rewards.js ────────────────────────────────────────────

async function rewardsRowsOnce() {
  const rows = [];
  const container = new El("div");
  container.appendChild = (child) => {
    rows.push(child);
    return child;
  };
  installDom({
    query: (s) => ({ ".loyalty-rewards-popup__rewards": container })[s] ?? null,
    create: (tag) => {
      const el = new El(tag);
      // createFloatingButton renders markup with innerHTML, then looks the button up.
      el._sel = (s) => (s === ".loyalty-rewards-btn" ? new El("button") : null);
      return el;
    },
  });
  window.loyaltyConfig = {
    direction: "ltr",
    textRewards: "Rewards",
    textLoyaltyOptions: "{points} points = {percentage} off",
    currencyCode: "SAR",
    cartTotalValue: 200,
  };
  let fetches = 0;
  window.zid = {
    cart: {
      getRedemptionMethods: () => {
        fetches += 1;
        return Promise.resolve({
          options: [
            { id: "m1", is_active: true, points_to_redeem: 100, reward: { discount_value: 10 } },
            { id: "m2", is_active: true, points_to_redeem: 200, reward: { discount_value: 20 } },
            { id: "m3", is_active: false, points_to_redeem: 50, reward: { discount_value: 5 } },
          ],
        });
      },
    },
  };
  const mod = await loadModule("assets/js/features/loyalty-rewards.js", {
    root: ROOT,
    expose: ["init"],
  });
  await settle();
  await settle();
  const afterFirst = rows.length;
  mod.init();
  await settle();
  await settle();
  const r = new Recorder();
  r.eq("every active method listed once", afterFirst, 2);
  r.eq("second init adds no rows", rows.length, 2);
  r.eq("the popup was fetched twice", fetches, 2);

  return { name: "RewardsRowsOnce", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

// ── refresh.js: failure falls back to a reload ─────────────────────────────

async function refreshFailureFallback() {
  const dom = refreshDom();
  globalThis.fetch = () => Promise.reject(new Error("network"));
  const refresh = await loadModule("assets/js/cart/refresh.js", {
    root: ROOT,
    stub: [
      "const updatePaymentWidgets = () => {};",
      "const updateLoyaltyDisplay = () => {};",
      "const setupCouponInput = () => {};",
      "const initAuthVisibility = () => {};",
    ].join("\n"),
    expose: ["refreshCartPage", "setCartLoadingState", "isCartRefreshing"],
  });
  const r = new Recorder();
  const productsList = dom.map["[data-cart-products-list]"];
  refresh.setCartLoadingState(true);
  r.eq("loading sets aria-busy", productsList.getAttribute("aria-busy"), "true");
  await refresh.refreshCartPage();
  await settle();
  r.eq("failed refresh reloads once", window.__reloads, 1);
  r.eq("failed refresh clears the loading state", productsList.getAttribute("aria-busy"), "false");
  r.eq("failed refresh clears the pointer lock", productsList.style.pointerEvents, "");
  r.eq("refreshing flag released", refresh.isCartRefreshing(), false);

  return { name: "RefreshFailureFallback", holds: r.failures.length === 0, detail: r.failures.slice(0, 3) };
}

// ── runner ─────────────────────────────────────────────────────────────────

const PROPERTY_NAMES = {
  totalsRows: "TotalsRows",
  discountSign: "DiscountSign",
  totalsTextEscaping: "TotalsTextEscaping",
  progressWidth: "ProgressWidth",
  quantityBounds: "QuantityBounds",
  quantityMirrorsDisplay: "QuantityMirrorsDisplay",
  quantityTargets: "QuantityTargets",
  qtyFailureSurfaces: "QtyFailureSurfaces",
  couponFormState: "CouponFormState",
  couponSubmitOnce: "CouponSubmitOnce",
  redemptionRecovers: "RedemptionRecovers",
  giftDeleteRecovers: "GiftDeleteRecovers",
  badgeConsistency: "BadgeConsistency",
  badgeOnRefresh: "BadgeOnRefresh",
  controllerInitOnce: "ControllerInitOnce",
  addToCartBindsOnce: "AddToCartBindsOnce",
  giftPopupTimer: "GiftPopupTimer",
  rewardsRowsOnce: "RewardsRowsOnce",
  refreshFailureFallback: "RefreshFailureFallback",
};

const PROPERTIES = [
  totalsRows,
  discountSign,
  totalsTextEscaping,
  progressWidth,
  quantityBounds,
  quantityMirrorsDisplay,
  quantityTargets,
  qtyFailureSurfaces,
  couponFormState,
  couponSubmitOnce,
  redemptionRecovers,
  giftDeleteRecovers,
  badgeConsistency,
  badgeOnRefresh,
  controllerInitOnce,
  addToCartBindsOnce,
  giftPopupTimer,
  rewardsRowsOnce,
  refreshFailureFallback,
];

let changed = 0;
for (const property of PROPERTIES) {
  let result;
  try {
    result = await property();
  } catch (err) {
    result = {
      name: PROPERTY_NAMES[property.name] || property.name,
      holds: null,
      detail: [`threw: ${err && err.stack ? err.stack.split("\n")[0] : err}`],
    };
  }
  const got = result.holds === null ? "error" : result.holds ? "holds" : "violation";
  const want = EXPECTED[result.name];
  if (got === want) {
    report(`ok       ${result.name}: ${got}`);
    if (got === "violation" && FINDINGS[result.name]) report(`FINDING: ${FINDINGS[result.name]}`);
  } else {
    changed += 1;
    report(`CHANGED  ${result.name}: recorded ${want}, now ${got}`);
    for (const line of result.detail || []) report(`         ${line}`);
  }
}
report(
  changed === 0
    ? `js properties: ${PROPERTIES.length} checks, every outcome matches the record`
    : `js properties: ${changed} outcome(s) changed`
);
process.exit(changed === 0 ? 0 : 1);
