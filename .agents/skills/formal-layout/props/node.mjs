/**
 * Formal properties over the layout group's JS utils, run on the REAL modules from
 * $ROOT/assets/js with only the browser globals they touch stubbed. Stdlib only.
 *
 *   ROOT=<repo> node props/node.mjs
 *
 * Prints one `PROPERTY <id> <ok|finding> <signature>` line per property.
 */
import { pathToFileURL } from "node:url";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = process.env.ROOT || ".";
const SEED = 20261111;

// ── deterministic randomness (printed so a finding is reproducible) ──────────
function mulberry32(seed) {
  let a = seed >>> 0;
  return function next() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick(rand, items) {
  return items[Math.floor(rand() * items.length)];
}

const results = [];
function report(id, violations, signature) {
  const status = violations.length === 0 ? "ok" : "finding";
  results.push({ id, status, signature });
  console.log(`PROPERTY ${id} ${status} ${signature}`);
  for (const line of violations.slice(0, 8)) console.log(`    ${line}`);
}

// ── fake browser surface ────────────────────────────────────────────────────
function makeLocation(origin, pathname = "/products/example", search = "", hash = "") {
  const navigations = [];
  const location = {
    origin,
    pathname,
    search,
    hash,
    _href: origin + pathname,
    get href() {
      return this._href;
    },
    set href(value) {
      navigations.push(value);
      this._href = value;
    },
  };
  return { location, navigations };
}

function makeDocument() {
  const listeners = [];
  return {
    readyState: "loading",
    listeners,
    addEventListener(type, handler) {
      listeners.push({ type, handler });
    },
    removeEventListener() {},
    querySelectorAll() {
      return [];
    },
    querySelector() {
      return null;
    },
    getElementById() {
      return null;
    },
    dispatchEvent() {
      return true;
    },
  };
}

// ── N1: no login redirect may leave the store's origin ──────────────────────
const REDIRECT_PAYLOADS = [
  "",
  "/account",
  "/products/example?x=1#frag",
  "//attacker.test/collect",
  "///attacker.test/collect",
  "/\\attacker.test/collect",
  "\\\\attacker.test/collect",
  "\\/attacker.test",
  "https://attacker.test/collect",
  "http://attacker.test",
  "https://store.test.evil.test/",
  "https://store.test@attacker.test/",
  "https://store.test:443@attacker.test/",
  "javascript:alert(1)",
  "JavaScript:alert(1)",
  "data:text/html,<script>alert(1)</script>",
  "vbscript:msgbox(1)",
  "file:///etc/passwd",
  "http://[",
  "http://",
  "https:attacker.test",
  " https://attacker.test",
  "\t//attacker.test",
  "\n//attacker.test",
  "http://attacker.test\\@store.test/",
  "/%2f%2fattacker.test",
  "/..//attacker.test",
  "/.%2e/attacker.test",
  "?next=https://attacker.test",
  "#//attacker.test",
  "http://localhost:8995/ok",
  "HTTP://ATTACKER.TEST",
  "http://attacker.test:80/",
  "//127.0.0.1:1/x",
  "/products/%0d%0aLocation:%20https://attacker.test",
  "‮//attacker.test",
  "\u0000//attacker.test",
  "/account\u0000.html",
  "attacker.test",
  "//attacker.test/%2e%2e/x",
  "////attacker.test",
  "https://attacker.test/?a=b#c",
  "/locales/ar?redirect_to=%2F%2Fattacker.test",
  "https://إattacker.test",
  "http://attacker.test\u0009",
];

function isSameOriginPath(target, origin) {
  if (typeof target !== "string" || target.length === 0) return false;
  try {
    return new URL(target, origin).origin === origin;
  } catch {
    return false;
  }
}

async function propAuthRedirect() {
  const origin = "https://store.test";
  const { location, navigations } = makeLocation(origin);
  const document = makeDocument();
  globalThis.window = {
    location,
    layoutConfig: { profileUrl: "/account" },
    addEventListener() {},
    removeEventListener() {},
    customerAuthState: undefined,
    auth_dialog: undefined,
  };
  globalThis.document = document;
  delete globalThis.zid;

  const mod = await import(pathToFileURL(join(ROOT, "assets/js/features/layout.js")).href);
  const state = globalThis.window[Symbol.for("growth-theme.layout-state")];
  const rand = mulberry32(SEED);
  const alphabet = "/\\:@.%#?&=-_~'\">< ;()[]{}|^$*+!,0123456789abcXYZ\u0000\u202e\u00e9";
  const random = Array.from({ length: 2000 }, () =>
    Array.from({ length: 1 + Math.floor(rand() * 24) }, () => pick(rand, alphabet.split(""))).join("")
  );
  const corpus = [...REDIRECT_PAYLOADS, ...random];

  const violations = [];
  const escapes = [];
  for (const target of corpus) {
    // Branch 1: signed-in shopper navigates straight to the normalized target.
    navigations.length = 0;
    state.pendingAuthRedirect = null;
    globalThis.window.customerAuthState = { isAuthenticated: true, isGuest: false };
    globalThis.window.auth_dialog = undefined;
    mod.handleLoginAction(target, false);
    const direct = navigations[0];
    if (direct === undefined) {
      violations.push(`signed-in ${JSON.stringify(target)}: no navigation`);
    } else if (!isSameOriginPath(direct, origin)) {
      violations.push(`signed-in ${JSON.stringify(target)} -> ${direct}`);
      escapes.push(target);
    }

    // Branch 2: guest, dialog present - the pending post-login redirect must be same-origin.
    navigations.length = 0;
    state.pendingAuthRedirect = null;
    globalThis.window.customerAuthState = { isAuthenticated: false, isGuest: true };
    let opens = 0;
    globalThis.window.auth_dialog = { open: () => (opens += 1) };
    mod.handleLoginAction(target, false);
    const pending = state.pendingAuthRedirect;
    if (!isSameOriginPath(pending, origin)) {
      violations.push(`guest ${JSON.stringify(target)}: pending ${JSON.stringify(pending)}`);
      escapes.push(target);
    }
    if (opens !== 1) violations.push(`guest ${JSON.stringify(target)}: dialog opened ${opens}x`);

    // Branch 3: no dialog at all - the login fallback carries the normalized target.
    navigations.length = 0;
    state.pendingAuthRedirect = null;
    globalThis.window.auth_dialog = undefined;
    mod.handleLoginAction(target, false);
    const fallback = navigations[0] || "";
    if (!fallback.startsWith("/auth/login?redirect_to=")) {
      violations.push(`fallback ${JSON.stringify(target)} -> ${JSON.stringify(fallback)}`);
    }
    const carried = decodeURIComponent(fallback.split("redirect_to=")[1] || "");
    if (!isSameOriginPath(carried, origin)) {
      violations.push(`fallback ${JSON.stringify(target)}: redirect_to ${JSON.stringify(carried)}`);
      escapes.push(target);
    }
  }
  const minimal = escapes.slice().sort((a, b) => a.length - b.length || (a < b ? -1 : 1))[0] || "-";
  report(
    "auth-redirect",
    violations,
    violations.length ? `escapes=${new Set(escapes).size},minimal=${minimal}` : `cases=${corpus.length}`
  );
}

// ── N2: stored customer location is accepted only when it is current and well formed ──
async function propLocationGate() {
  const store = new Map();
  const session = new Map();
  globalThis.localStorage = {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
  };
  globalThis.sessionStorage = {
    getItem: (key) => (session.has(key) ? session.get(key) : null),
    setItem: (key, value) => session.set(key, String(value)),
  };
  const modal = { dataset: {} };
  globalThis.document = { getElementById: (id) => (id === "product-quick-view-modal" ? modal : null) };
  globalThis.window = {};
  delete globalThis.window.region_settings_dialog;

  const mod = await import(pathToFileURL(join(ROOT, "assets/js/utils/customer-location.js")).href);
  const NOW = 1_700_000_000_000;
  const REAL_NOW = Date.now();
  const violations = [];

  function expectedHasLocation(value) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
    const selection = value.confirmedSelection;
    if (typeof selection !== "object" || selection === null || Array.isArray(selection)) return false;
    if (typeof selection.cityId !== "string") return false;
    if (typeof selection.expiresAt !== "number" || !Number.isFinite(selection.expiresAt)) return false;
    if (selection.latitude !== undefined && typeof selection.latitude !== "number") return false;
    if (selection.longitude !== undefined && typeof selection.longitude !== "number") return false;
    return Boolean(selection.cityId) && selection.expiresAt > NOW;
  }

  function run(raw) {
    store.set("zid_kit_select_branch", raw);
    return mod.hasStoredCustomerLocation(NOW);
  }

  const curated = [
    undefined,
    "",
    "null",
    "[]",
    "[1,2]",
    "{}",
    JSON.stringify({ branchData: { type: "delivery" }, cityId: "42" }),
    JSON.stringify({ confirmedSelection: null }),
    JSON.stringify({ confirmedSelection: [] }),
    JSON.stringify({ confirmedSelection: { cityId: "42", expiresAt: NOW + 1 } }),
    JSON.stringify({ confirmedSelection: { cityId: "42", expiresAt: NOW } }),
    JSON.stringify({ confirmedSelection: { cityId: "42", expiresAt: NOW - 1 } }),
    JSON.stringify({ confirmedSelection: { cityId: "", expiresAt: NOW + 1 } }),
    JSON.stringify({ confirmedSelection: { cityId: 42, expiresAt: NOW + 1 } }),
    JSON.stringify({ confirmedSelection: { cityId: "42", expiresAt: String(NOW + 1) } }),
    JSON.stringify({ confirmedSelection: { cityId: "42", expiresAt: NOW + 1, latitude: "24.7" } }),
    JSON.stringify({ confirmedSelection: { cityId: "42", expiresAt: NOW + 1, latitude: 24.7, longitude: 46.6 } }),
    '{"confirmedSelection":{"cityId":"42","expiresAt":Infinity}}',
    '{"confirmedSelection":{"cityId":"42","expiresAt":NaN}}',
    '{"confirmedSelection":{"cityId":"42","expiresAt":1e999}}',
    "not json",
    "  ",
  ];
  for (const raw of curated) {
    const parsed = (() => {
      try {
        return raw === undefined ? undefined : JSON.parse(raw);
      } catch {
        return "unparseable";
      }
    })();
    const want = parsed === undefined || parsed === "unparseable" ? false : expectedHasLocation(parsed);
    const got = run(raw === undefined ? null : raw);
    if (got !== want) violations.push(`${JSON.stringify(raw)}: ${got} want ${want}`);
  }

  // Seeded random JSON documents: shape mutations that a naive reader would accept.
  const rand = mulberry32(SEED + 1);
  const leaf = () =>
    pick(rand, [
      "42",
      "",
      "city",
      0,
      -1,
      NOW,
      NOW + 1,
      NOW - 1,
      null,
      true,
      false,
      [],
      {},
      "1e999",
    ]);
  const value = (depth) => {
    if (depth <= 0) return leaf();
    const roll = rand();
    if (roll < 0.35) return leaf();
    if (roll < 0.6) return [value(depth - 1), value(depth - 1)];
    const obj = {};
    for (const key of ["confirmedSelection", "cityId", "expiresAt", "latitude", "longitude", "branchData"]) {
      if (rand() < 0.5) obj[key] = depth === 2 && key === "confirmedSelection" ? value(depth - 1) : leaf();
    }
    return obj;
  };
  for (let i = 0; i < 400; i += 1) {
    const doc = value(2);
    const want = expectedHasLocation(doc);
    const got = run(JSON.stringify(doc));
    if (got !== want) violations.push(`random ${JSON.stringify(doc)}: ${got} want ${want}`);
  }

  // Hostile storage must not throw: fail closed on read, fail open on the gate.
  const realGetItem = globalThis.localStorage.getItem;
  globalThis.localStorage.getItem = () => {
    throw new Error("storage blocked");
  };
  if (mod.hasStoredCustomerLocation(NOW) !== false) violations.push("throwing localStorage: not false");
  globalThis.localStorage.getItem = realGetItem;

  // Gate truth table: enabled x mode x stored x fail-open flag x mounted dialog.
  const gateViolations = [];
  for (const enabled of ["true", "false"]) {
    for (const mode of ["required_on_add_to_cart", "optional"]) {
      for (const stored of [false, true]) {
        for (const failedOpen of [false, true]) {
          for (const mounted of [false, true]) {
            modal.dataset = { locationSelectionEnabled: enabled, locationSelectionMode: mode };
            store.clear();
            session.clear();
            if (stored) {
              store.set(
                "zid_kit_select_branch",
                JSON.stringify({ confirmedSelection: { cityId: "42", expiresAt: REAL_NOW + 60000 } })
              );
            }
            if (failedOpen) session.set("zid_customer_location_selection_fail_open", "true");
            let opens = 0;
            globalThis.window.region_settings_dialog = mounted ? { open: () => (opens += 1) } : undefined;
            const want = enabled === "true" && mode === "required_on_add_to_cart" && !stored && !failedOpen && mounted;
            const got = mod.requestRequiredCustomerLocation();
            if (got !== want || opens !== (want ? 1 : 0)) {
              gateViolations.push(
                `enabled=${enabled} mode=${mode} stored=${stored} failOpen=${failedOpen} mounted=${mounted}:` +
                  ` returns ${got} opens ${opens}, want ${want}`
              );
            }
            // The client-side dialog object, but without open(): still fail open.
            if (mounted) {
              globalThis.window.region_settings_dialog = {};
              if (mod.requestRequiredCustomerLocation() !== false) {
                gateViolations.push(`open() missing: gate still deferred`);
              }
            }
          }
        }
      }
    }
  }
  violations.push(...gateViolations);
  report(
    "location-gate",
    violations,
    violations.length ? `violations=${violations.length}` : "cases=curated+400+32"
  );
}

// ── N3: phone length verdicts follow the declared table ────────────────────
async function propCountryTable() {
  globalThis.window = {};
  const mod = await import(pathToFileURL(join(ROOT, "assets/js/data/countries.js")).href);
  const { CountriesData, validatePhoneLength, isPossiblePhoneNumber, getByCode, getByDialCode } = mod;
  const violations = [];

  const codes = new Set();
  for (const country of CountriesData) {
    if (codes.has(country.code)) violations.push(`duplicate code ${country.code}`);
    codes.add(country.code);
    if (!/^[A-Z]{2}$/.test(country.code)) violations.push(`bad code ${country.code}`);
    if (!/^\+\d{1,4}$/.test(country.dialCode)) violations.push(`${country.code}: dial ${country.dialCode}`);
    if (!country.name || !country.nameAr) violations.push(`${country.code}: missing name`);
    const lengths = country.phoneLengths || [];
    if (lengths.some((n) => !Number.isInteger(n) || n < 4 || n > 15)) {
      violations.push(`${country.code}: phoneLengths ${JSON.stringify(lengths)}`);
    }
    if ([...lengths].sort((a, b) => a - b).join() !== lengths.join()) {
      violations.push(`${country.code}: phoneLengths not sorted`);
    }
    if (getByCode(country.code) !== country) violations.push(`${country.code}: getByCode mismatch`);
    if (getByDialCode(country.dialCode).dialCode !== country.dialCode) {
      violations.push(`${country.code}: getByDialCode(${country.dialCode}) mismatch`);
    }

    for (let length = 0; length <= 20; length += 1) {
      const digits = "1".repeat(length);
      const got = validatePhoneLength(digits, country.code);
      let want;
      if (lengths.length === 0) {
        want = length < 7 ? "TOO_SHORT" : length > 15 ? "TOO_LONG" : undefined;
      } else {
        const min = Math.min(...lengths);
        const max = Math.max(...lengths);
        want = length < min ? "TOO_SHORT" : length > max ? "TOO_LONG" : lengths.includes(length) ? undefined : "INVALID_LENGTH";
      }
      if (got !== want) violations.push(`${country.code} len ${length}: ${got} want ${want}`);
      if (isPossiblePhoneNumber(digits, country.code) !== (got === undefined)) {
        violations.push(`${country.code} len ${length}: isPossiblePhoneNumber disagrees`);
      }
      // Formatting is not part of the number: the same digits, spaced out, get the same verdict.
      const pretty = digits.replace(/(\d{2})/g, "$1 - ").trim();
      if (validatePhoneLength(pretty, country.code) !== got) {
        violations.push(`${country.code} len ${length}: formatting changed the verdict`);
      }
    }
  }
  if (validatePhoneLength("123456789", "ZZ") !== "INVALID_COUNTRY") violations.push("unknown code not INVALID_COUNTRY");
  if (validatePhoneLength("123456789", "+999999") !== "INVALID_COUNTRY") violations.push("unknown dial not INVALID_COUNTRY");

  // components/ui/phone-input.jinja ships its own default list; it must agree with this table.
  const template = readFileSync(join(ROOT, "components/ui/phone-input.jinja"), "utf8");
  const defaults = [...template.matchAll(/"code":\s*"([A-Z]{2})",\s*"dial_code":\s*"(\+\d+)"/g)];
  if (defaults.length !== 18) violations.push(`phone-input defaults: ${defaults.length} entries`);
  for (const [, code, dial] of defaults) {
    const entry = getByCode(code);
    if (!entry) violations.push(`phone-input default ${code} missing from CountriesData`);
    else if (entry.dialCode !== dial) {
      violations.push(`phone-input default ${code}: template ${dial}, table ${entry.dialCode}`);
    }
  }
  report(
    "country-table",
    violations,
    violations.length ? `violations=${violations.length}` : `countries=${CountriesData.length},defaults=18`
  );
}

// ── N4: dispatch/on keep listener bookkeeping exact ────────────────────────
async function propEvents() {
  const calls = [];
  class RecordingTarget {
    constructor() {
      this.listeners = new Map();
    }
    addEventListener(type, handler, options) {
      calls.push(["add", type, handler, options]);
      this.listeners.set(handler, type);
    }
    removeEventListener(type, handler, options) {
      calls.push(["remove", type, handler, options]);
      this.listeners.delete(handler);
    }
    dispatchEvent(event) {
      for (const [handler, type] of this.listeners) if (type === event.type) handler(event);
      return true;
    }
  }
  const windowTarget = new RecordingTarget();
  globalThis.window = windowTarget;
  const mod = await import(pathToFileURL(join(ROOT, "assets/js/utils/events.js")).href);
  const violations = [];

  let seen = null;
  mod.dispatch("cart:added", { id: 7 });
  if (windowTarget.listeners.size !== 0) violations.push("dispatch created listeners");
  const off = mod.on(windowTarget, "cart:added", (event) => (seen = event));
  mod.dispatch("cart:added", { id: 7 });
  if (!seen) violations.push("dispatch did not reach the listener on the default target");
  else {
    if (seen.detail.id !== 7) violations.push(`detail lost: ${JSON.stringify(seen.detail)}`);
    if (seen.type !== "cart:added") violations.push(`type ${seen.type}`);
    if (seen.bubbles !== true) violations.push("dispatched event does not bubble");
  }
  const [add] = calls;
  if (!add || add[0] !== "add" || add[1] !== "cart:added") violations.push("on() did not add the listener");

  off();
  const remove = calls[calls.length - 1];
  if (!remove || remove[0] !== "remove" || remove[1] !== "cart:added") violations.push("cleanup did not remove");
  else if (remove[2] !== add[2] || remove[3] !== add[3]) violations.push("cleanup used a different handler/options");
  seen = null;
  mod.dispatch("cart:added", { id: 8 });
  if (seen) violations.push("handler still fires after cleanup");
  off();
  if (windowTarget.listeners.size !== 0) violations.push("double cleanup changed listener count");

  // Two listeners, one cleaned: the other keeps firing, and options survive the round trip.
  let a = 0;
  let b = 0;
  const offA = mod.on(windowTarget, "content:loaded", () => (a += 1), { passive: true });
  mod.on(windowTarget, "content:loaded", () => (b += 1));
  mod.dispatch("content:loaded");
  if (a !== 1 || b !== 1) violations.push(`two listeners: a=${a} b=${b}`);
  offA();
  mod.dispatch("content:loaded");
  if (a !== 1 || b !== 2) violations.push(`after one cleanup: a=${a} b=${b}`);
  const passive = calls.find((c) => c[0] === "add" && c[1] === "content:loaded" && c[3]);
  if (!passive || passive[3].passive !== true) violations.push("options were not forwarded to addEventListener");

  // An explicit target must not leak to window.
  const other = new RecordingTarget();
  let otherHits = 0;
  let windowHits = 0;
  mod.on(other, "x", () => (otherHits += 1));
  mod.on(windowTarget, "x", () => (windowHits += 1));
  mod.dispatch("x", {}, other);
  if (otherHits !== 1 || windowHits !== 0) violations.push(`explicit target: other=${otherHits} window=${windowHits}`);
  report("events", violations, violations.length ? `first=${violations[0]}` : "cases=11");
}

async function main() {
  await propAuthRedirect();
  await propLocationGate();
  await propCountryTable();
  await propEvents();
  const findings = results.filter((r) => r.status !== "ok");
  console.log(`# seed ${SEED}; ${results.length} properties, ${findings.length} finding(s)`);
}

main().catch((error) => {
  console.error(`PROPERTY harness error ${error && error.stack ? error.stack : error}`);
  process.exit(2);
});
