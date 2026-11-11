/**
 * P1 — js/time-ago.js relative-time contract (Node, stdlib only).
 *
 * Imports the REAL module from $ROOT/assets/js/time-ago.js with the smallest
 * DOM it needs, then checks every offset against the contract the labels
 * promise: the largest unit that fits, floored (never rounded), singular only
 * for 1, "just now" only under a minute, and no label that goes backwards as
 * time moves forward.
 *
 * Usage: node --experimental-vm-modules props/time_ago.mjs [--root DIR]
 * Exit 0 when the property holds, 1 with the counterexample otherwise.
 */

import { pathToFileURL } from "node:url";
import path from "node:path";

const ROOT = (() => {
  const i = process.argv.indexOf("--root");
  return i > -1 ? process.argv[i + 1] : process.cwd();
})();

const UNITS = [
  ["year", "years", 31536000],
  ["month", "months", 2592000],
  ["week", "weeks", 604800],
  ["day", "days", 86400],
  ["hour", "hours", 3600],
  ["minute", "minutes", 60]
];
const RANK = new Map(UNITS.map(([one, , seconds], index) => [one, index]));

const el = (date) => ({ getAttribute: () => date, textContent: "" });
let nodes = [];
let labelsNode = null;

globalThis.window = globalThis;
globalThis.setInterval = () => 0;
globalThis.document = {
  readyState: "complete",
  addEventListener() {},
  querySelector: (selector) => (selector.includes("time-ago-labels") ? labelsNode : null),
  querySelectorAll: () => nodes
};

await import(pathToFileURL(path.join(ROOT, "assets/js/time-ago.js")).href);

/** Render one age through the real module and return its label. */
function labelFor(ageSeconds, labels = null) {
  const when = new Date(Date.now() - ageSeconds * 1000);
  // "YYYY-MM-DD HH:MM:SS" is what vitrin prints into data-time-ago-date, and
  // browsers read it as local time, so build it from local parts.
  const pad = (n) => String(n).padStart(2, "0");
  const stamp =
    `${when.getFullYear()}-${pad(when.getMonth() + 1)}-${pad(when.getDate())} ` +
    `${pad(when.getHours())}:${pad(when.getMinutes())}:${pad(when.getSeconds())}`;
  nodes = [el(stamp)];
  labelsNode = labels ? { dataset: { timeAgoLabels: JSON.stringify(labels) } } : null;
  globalThis.window.updateTimeAgoElements();
  return nodes[0].textContent;
}

const PLURAL = { year: "years", month: "months", week: "weeks", day: "days", hour: "hours", minute: "minutes" };

function problemsFor(age) {
  const out = labelFor(age);
  const problems = [];
  if (out === "Just now") {
    if (age >= 60) problems.push(`${age}s says "Just now"`);
    return problems;
  }
  const match = /^(\d+) (year|month|week|day|hour|minute)s? ago$/.exec(out);
  if (!match) {
    problems.push(`${age}s produced ${JSON.stringify(out)}`);
    return problems;
  }
  const count = Number(match[1]);
  const unit = match[2];
  const seconds = UNITS.find(([one]) => one === unit)[2];
  if (count < 1) problems.push(`${age}s produced a zero count`);
  // floored: count fits, count+1 does not
  if (count * seconds > age) problems.push(`${age}s rounds up to ${count} ${unit}`);
  if ((count + 1) * seconds <= age) problems.push(`${age}s rounds down to ${count} ${unit}`);
  // largest unit that fits
  for (const [one, , size] of UNITS) {
    if (RANK.get(one) < RANK.get(unit) && age >= size) {
      problems.push(`${age}s picked ${unit} while ${one} also fits`);
      break;
    }
  }
  const plural = count > 1;
  const said = match[0].slice(match[1].length + 1).replace(" ago", "");
  if (plural !== (said === PLURAL[unit])) problems.push(`${age}s plural mismatch (${said})`);
  return problems;
}

// Bounds: every unit edge (±1s), plus a deterministic spread out to two years.
const ages = new Set([0, 1, 59, 60, 61]);
for (const [, , size] of UNITS) {
  for (const delta of [-1, 0, 1, 2]) if (size + delta >= 0) ages.add(size + delta);
}
for (let i = 0; i <= 240; i += 1) ages.add(Math.floor((i / 240) * 2 * 31536000));
const ordered = [...ages].sort((a, b) => a - b);

let failures = [];
for (const age of ordered) for (const problem of problemsFor(age)) failures.push(problem);

// Monotonicity: as the age grows the unit never gets smaller and, inside a unit,
// the count never gets smaller.
let previous = null;
for (const age of ordered) {
  const out = labelFor(age);
  const match = /^(\d+) (year|month|week|day|hour|minute)s? ago$/.exec(out);
  if (!match) continue;
  const current = { rank: RANK.get(match[2]), count: Number(match[1]) };
  if (previous) {
    if (current.rank > previous.rank) failures.push(`${age}s moved to a smaller unit`);
    if (current.rank === previous.rank && current.count < previous.count) {
      failures.push(`${age}s count went backwards inside ${match[2]}`);
    }
  }
  previous = current;
}

// Localised labels: the page supplies them through one JSON data attribute.
const arabic = {
  year: "سنة",
  years: "سنوات",
  month: "شهر",
  months: "أشهر",
  week: "أسبوع",
  weeks: "أسابيع",
  day: "يوم",
  days: "أيام",
  hour: "ساعة",
  hours: "ساعات",
  minute: "دقيقة",
  minutes: "دقائق",
  ago: "منذ %s",
  justNow: "الآن"
};
const localised = labelFor(2 * 86400, arabic);
if (localised !== "منذ 2 أيام") failures.push(`localised label was ${JSON.stringify(localised)}`);
const oneDay = labelFor(86400, arabic);
if (oneDay !== "منذ 1 يوم") failures.push(`localised singular was ${JSON.stringify(oneDay)}`);

// A broken labels payload must fall back to English instead of throwing.
labelsNode = { dataset: { timeAgoLabels: "{not json" } };
nodes = [el("2026-01-01 00:00:00")];
const warnings = [];
const warn = console.warn;
console.warn = (...args) => warnings.push(args.join(" "));
try {
  globalThis.window.updateTimeAgoElements();
} catch (error) {
  failures.push(`bad labels JSON threw ${error}`);
} finally {
  console.warn = warn;
  labelsNode = null;
}

if (failures.length) {
  console.log(`CHANGED P1 time-ago-buckets :: expected holds, got FAIL :: ${failures.slice(0, 6).join("; ")}`);
  process.exit(1);
}
console.log(
  `PASS P1 time-ago-buckets :: ${ordered.length} offsets (0..2y, every unit edge), ` +
    `monotone, localised labels, bad-JSON fallback`
);
