// formal-home-sections P6/P7: run the REAL inline countdown script of sections/countdown.jinja in a
// node:vm with a fake clock and fake DOM, over a fixed set of end dates and tick schedules.
// Only the two Jinja interpolations ({{ sectionId }}, {{ settings.end_date }}) are substituted.
import { readFileSync } from "node:fs";
import vm from "node:vm";
import path from "node:path";

const ROOT = process.env.ROOT;
const tpl = readFileSync(path.join(ROOT, "sections/countdown.jinja"), "utf8");
const body = tpl.split("<script>")[1].split("</script>")[0];

const SEED = 20261111; // mulberry32
let a = SEED;
const rnd = () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
console.log(`NOTE seed ${SEED}`);

function run(endMs, startNow, tickGaps) {
  let now = startNow;
  class FakeDate extends Date {
    constructor(...args) { if (args.length === 0) super(now); else super(...args); }
    static now() { return now; }
  }
  const mk = () => ({ textContent: " 00 ", style: {} });
  const els = { ".days-value": mk(), ".hours-value": mk(), ".minutes-value": mk(), ".seconds-value": mk(), ".countdown-content": mk() };
  const section = { style: {}, querySelector: (s) => els[s] };
  let timer = null, cleared = false, writesAfterHide = 0;
  const ctx = {
    document: { querySelector: () => section },
    Date: FakeDate, isNaN, String, Math, Number, parseInt,
    setInterval: (fn) => { timer = fn; return 1; },
    clearInterval: () => { cleared = true; timer = null; },
  };
  const iso = new Date(endMs).toISOString();
  vm.runInNewContext(body.replace("{{ sectionId }}", "x").replace("{{ settings.end_date }}", iso), ctx);
  const frames = [];
  const read = () => ({ d: els[".days-value"].textContent, h: els[".hours-value"].textContent, m: els[".minutes-value"].textContent, s: els[".seconds-value"].textContent });
  frames.push({ at: now, ...read(), sectionHidden: section.style.display === "none", contentHidden: els[".countdown-content"].style.display === "none" });
  for (const gap of tickGaps) {
    if (!timer) break;
    now += gap;
    const before = JSON.stringify(read());
    timer();
    frames.push({ at: now, ...read(), sectionHidden: section.style.display === "none", contentHidden: els[".countdown-content"].style.display === "none" });
    if (section.style.display === "none" && JSON.stringify(read()) !== before) writesAfterHide++;
  }
  return { frames, cleared, timerAlive: timer !== null, writesAfterHide, section, content: els[".countdown-content"] };
}

const START = Date.UTC(2026, 10, 11, 12, 0, 0, 0);
const OFFSETS = [-86400000, -5000, -1, 0, 1, 999, 1000, 1001, 59999, 60000, 3599999, 3600000, 86399999, 86400000, 86400001, 90061001, 8640000000];
const bad = [];
let p7 = [];
for (const off of OFFSETS) {
  for (const sched of ["steady", "jitter", "throttled"]) {
    const gaps = [];
    const dist = off;
    const n = Math.min(Math.max(Math.ceil(Math.abs(dist) / 1000) + 4, 6), 12);
    for (let i = 0; i < n; i++) gaps.push(sched === "steady" ? 1000 : sched === "jitter" ? 1000 + Math.floor(rnd() * 800) : 1000 + Math.floor(rnd() * 90000));
    // long countdowns: also jump close to the end so the expiry tick is exercised
    if (dist > 20000) { gaps.length = 3; gaps.push(dist - 3000 - gaps.reduce((x, y) => x + y, 0)); gaps.push(1000, 1000, 1000, 1000, 1000); }
    const r = run(START + off, START, gaps);
    const key = `end=now${off >= 0 ? "+" : ""}${off}ms sched=${sched}`;
    if (off <= 0) {
      // P7: ended before load. Expectation derived from the script's own expiry branch: the whole section hides.
      const f = r.frames[0];
      if (!f.sectionHidden) p7.push(`end=now${off >= 0 ? "+" : ""}${off}ms: only .countdown-content hidden (section display=${JSON.stringify(r.section.style.display)}), section keeps its min-height box`);
      continue;
    }
    let lastTotal = Infinity, hidden = false;
    for (const f of r.frames) {
      const dist = START + off - f.at;
      if (hidden) continue;
      if (f.sectionHidden) { hidden = true; if (dist >= 0) bad.push(`${key}: hidden early at distance ${dist}`); continue; }
      if (dist < 0) { bad.push(`${key}: still visible at distance ${dist}`); continue; }
      const vals = [f.d, f.h, f.m, f.s];
      if (!vals.every((v) => /^\d{2,}$/.test(v))) bad.push(`${key}: non-numeric/negative field ${JSON.stringify(vals)} at distance ${dist}`);
      const [d, h, m, s] = vals.map(Number);
      if (h > 23 || m > 59 || s > 59) bad.push(`${key}: field out of range ${vals}`);
      const total = d * 86400 + h * 3600 + m * 60 + s;
      if (total !== Math.floor(dist / 1000)) bad.push(`${key}: shows ${total}s, distance ${Math.floor(dist / 1000)}s`);
      if (total > lastTotal) bad.push(`${key}: countdown went up ${lastTotal} -> ${total}`);
      lastTotal = total;
    }
    if (r.writesAfterHide) bad.push(`${key}: wrote fields after hiding`);
    const last = r.frames[r.frames.length - 1];
    if (hidden && (!r.cleared || r.timerAlive)) bad.push(`${key}: interval not cleared at expiry`);
    if (!hidden && START + off - last.at < 0) bad.push(`${key}: ran past expiry without hiding`);
  }
}
// first paint: a future date shows the real remaining time in the first synchronous call
{
  const r = run(START + 90061001, START, []);
  const f = r.frames[0];
  if ([f.d, f.h, f.m, f.s].join(",") !== "01,01,01,01") bad.push(`first paint ${[f.d, f.h, f.m, f.s]}`);
}
// garbage / empty dates
for (const raw of ["", "not a date", "2020-13-45"]) {
  let now = START; let content = { style: {} };
  const section = { style: {}, querySelector: (s) => (s === ".countdown-content" ? content : { textContent: "" }) };
  vm.runInNewContext(body.replace("{{ sectionId }}", "x").replace("{{ settings.end_date }}", raw), { document: { querySelector: () => section }, Date, isNaN, String, Math, setInterval: () => 1, clearInterval() {} });
  if (content.style.display !== "none") bad.push(`bad date ${JSON.stringify(raw)}: content not hidden`);
}
const uniq = (xs) => [...new Set(xs)].sort();
console.log(bad.length ? `RESULT P6-countdown-never-negative finding ${uniq(bad).length}` : "RESULT P6-countdown-never-negative holds");
uniq(bad).slice(0, 12).forEach((b) => console.log(`  counterexample: ${b}`));
const p7u = uniq(p7);
console.log(p7u.length ? `RESULT P7-countdown-expired-at-load finding ${p7u.length}` : "RESULT P7-countdown-expired-at-load holds");
p7u.slice(0, 4).forEach((b) => console.log(`  counterexample: ${b}`));
