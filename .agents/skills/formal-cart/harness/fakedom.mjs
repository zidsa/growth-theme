/**
 * Minimal browser stand-ins for driving the cart modules under Node.
 *
 * The modules under test are imported unchanged (or, where an import would drag in a
 * module the property does not depend on, with that one import removed and replaced by
 * the stub named at the call site). What stands in is the *browser*: an EventTarget
 * element with dataset/classList/style/hidden/disabled/value, an EventTarget document
 * with querySelector/querySelectorAll, and an EventTarget window. Node's own Event,
 * CustomEvent and EventTarget are used, so `new CustomEvent("qty:change", {...})`
 * behaves as in a page.
 */

let loadCounter = 0;

export class El extends EventTarget {
  constructor(tag = "div", init = {}) {
    super();
    this.tagName = String(tag).toUpperCase();
    this.dataset = {};
    this.children = [];
    this.hidden = false;
    this.disabled = false;
    this.value = "";
    this.min = "";
    this.max = "";
    this._text = "";
    this.innerHTML = "";
    this.className = "";
    this.style = {};
    this.attributes = {};
    this.focused = 0;
    this._classes = new Set();
    const self = this;
    this.classList = {
      add(...names) {
        names.flat().forEach((n) => n && self._classes.add(n));
      },
      remove(...names) {
        names.flat().forEach((n) => self._classes.delete(n));
      },
      contains(name) {
        return self._classes.has(name);
      },
      toggle(name, force) {
        const want = force === undefined ? !self._classes.has(name) : Boolean(force);
        if (want) self._classes.add(name);
        else self._classes.delete(name);
        return want;
      },
      toString() {
        return [...self._classes].join(" ");
      },
    };
    Object.assign(this, init);
  }

  get textContent() {
    return this._text;
  }

  set textContent(value) {
    // The browser stores text as a string: `el.textContent = 4` reads back "4".
    this._text = value === null || value === undefined ? "" : String(value);
  }

  querySelector(selector) {
    return typeof this._sel === "function" ? this._sel(selector) : null;
  }

  querySelectorAll(selector) {
    return typeof this._selAll === "function" ? this._selAll(selector) : [];
  }

  closest(selector) {
    return typeof this._closest === "function" ? this._closest(selector) : null;
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === "hidden") this.hidden = true;
  }

  getAttribute(name) {
    return Object.prototype.hasOwnProperty.call(this.attributes, name)
      ? this.attributes[name]
      : null;
  }

  removeAttribute(name) {
    delete this.attributes[name];
    if (name === "hidden") this.hidden = false;
  }

  focus() {
    this.focused += 1;
  }

  click() {
    this.dispatchEvent(new Event("click", { bubbles: true }));
  }

  get offsetParent() {
    return this.hidden ? null : {};
  }
}

/**
 * Install document/window globals. `query`/`queryAll` resolve selectors for this test;
 * `create` builds elements for document.createElement.
 */
export function installDom({ query, queryAll, create, location } = {}) {
  const doc = new EventTarget();
  doc.readyState = "complete";
  doc.body = new El("body");
  doc.documentElement = new El("html");
  doc.querySelector = (selector) => (query ? query(selector) : null);
  doc.querySelectorAll = (selector) => (queryAll ? queryAll(selector) : []);
  doc.getElementById = (id) => (query ? query(`#${id}`) : null);
  doc.createElement = (tag) => (create ? create(tag) : new El(tag));
  doc.createElementNS = (_ns, tag) => new El(tag);
  doc.createTextNode = (text) => ({ nodeValue: text });

  const win = new EventTarget();
  win.document = doc;
  win.location = location || {
    href: "http://verify.local/cart",
    pathname: "/cart",
    search: "",
    reload() {
      win.__reloads = (win.__reloads || 0) + 1;
    },
  };
  win.navigator = { userAgent: "node" };
  win.setTimeout = setTimeout;
  win.clearTimeout = clearTimeout;

  // A browser exposes every `window.x` as a bare `x`; modules rely on that (`zid`,
  // `fetch`, `DOMParser` are read unqualified). Mirror writes onto globalThis, and bind
  // EventTarget methods to the real target so `window.addEventListener` keeps working.
  const winProxy = new Proxy(win, {
    get(target, key) {
      const value = target[key];
      return typeof value === "function" ? value.bind(target) : value;
    },
    set(target, key, value) {
      target[key] = value;
      if (typeof key === "string") globalThis[key] = value;
      return true;
    },
    has(target, key) {
      return key in target;
    },
  });

  globalThis.document = doc;
  globalThis.window = winProxy;

  /** Selectors registered on `document`, so a test can call a document-level listener. */
  const documentListeners = [];
  const addEventListener = doc.addEventListener.bind(doc);
  doc.addEventListener = (type, fn, opts) => {
    documentListeners.push({ type, fn });
    return addEventListener(type, fn, opts);
  };
  doc.listeners = (type) => documentListeners.filter((l) => l.type === type).map((l) => l.fn);

  return { doc, win: winProxy };
}

const IMPORT_BLOCK = /import\s+\{[^}]*\}\s+from\s+["'][^"']+["'];?/g;
const IMPORT_NAMESPACE = /import\s+\*\s+as\s+\w+\s+from\s+["'][^"']+["'];?/g;
const IMPORT_SIDE_EFFECT = /import\s+["'][^"']+["'];?/g;
const IMPORT_DEFAULT = /import\s+\w+\s+from\s+["'][^"']+["'];?/g;

/**
 * Import a module's source with every `import` statement removed, `stub` prepended, and
 * `expose` names published on `window.__mod`. Used only where the stripped import is a
 * module this property does not exercise; the call site names what it stubs.
 */
export async function loadModule(relPath, { stub = "", expose = [], root = "" } = {}) {
  const fs = await import("node:fs/promises");
  const src = await fs.readFile(`${root}/${relPath}`, "utf8");
  const stripped = src
    .replace(IMPORT_BLOCK, "")
    .replace(IMPORT_NAMESPACE, "")
    .replace(IMPORT_SIDE_EFFECT, "")
    .replace(IMPORT_DEFAULT, "");
  const bridge = expose.length ? `\nwindow.__mod = { ${expose.join(", ")} };` : "";
  const url =
    "data:text/javascript;base64," +
    Buffer.from(`${stub}\n${stripped}\n${bridge}`, "utf8").toString("base64") +
    `#${++loadCounter}`;
  await import(url);
  return globalThis.window.__mod;
}

/** Import a module straight from disk (no imports to strip). */
export async function importPlain(relPath, { root = "" } = {}) {
  const url = new URL(`file://${root}/${relPath}`);
  url.search = `?n=${++loadCounter}`;
  return import(url.href);
}

/** A parsed-document stand-in: the selectors refresh.js queries, with marker content. */
export function shadowDocument(map) {
  return {
    querySelector(selector) {
      return Object.prototype.hasOwnProperty.call(map, selector) ? map[selector] : null;
    },
  };
}

/** Assertion helper that records named checks instead of throwing on the first one. */
export class Recorder {
  constructor() {
    this.failures = [];
    this.count = 0;
  }

  ok(name, condition, detail) {
    this.count += 1;
    if (!condition) this.failures.push(`${name}: ${detail}`);
    return Boolean(condition);
  }

  eq(name, actual, expected) {
    return this.ok(
      name,
      JSON.stringify(actual) === JSON.stringify(expected),
      `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`
    );
  }
}
