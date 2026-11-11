/**
 * Run the rendered 404 countdown script (templates/404_not_found.jinja) against fake
 * timers and report what the shopper would see. Stdlib only.
 *
 *   node props/run_script.mjs /tmp/countdown.js
 */
import { readFileSync } from "node:fs";

const source = readFileSync(process.argv[2], "utf8");

const ticks = [];
const navigations = [];
let cleared = false;
let interval = null;

const countdownElement = {
  set textContent(value) {
    ticks.push(Number(value));
  },
  get textContent() {
    return String(ticks[ticks.length - 1]);
  },
};

const document = {
  getElementById(id) {
    return id === "redirectCountdown" ? countdownElement : null;
  },
};

const window = {
  location: {
    _href: "/current",
    get href() {
      return this._href;
    },
    set href(value) {
      navigations.push(value);
      this._href = value;
    },
  },
};

function setIntervalStub(fn) {
  interval = fn;
  return 1;
}

function clearIntervalStub(id) {
  if (id === 1) {
    cleared = true;
    interval = null;
  }
}

// The script is real template output: run it with only the browser surface it uses.
const run = new Function(
  "document",
  "window",
  "setInterval",
  "clearInterval",
  `${source}\nreturn typeof startRedirectCountdown === "function" ? startRedirectCountdown : null;`
);
const start = run(document, window, setIntervalStub, clearIntervalStub);

if (typeof start === "function" && !interval) {
  start(3);
}

// Advance the fake clock: at most 10 ticks, stopping once the interval is cleared.
for (let i = 0; i < 10 && interval; i += 1) {
  const tick = interval;
  tick();
}

process.stdout.write(
  JSON.stringify({
    ticks,
    navigations,
    cleared,
    pendingInterval: interval !== null,
  }) + "\n"
);
