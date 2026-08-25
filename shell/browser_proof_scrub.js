// XPDaily — Scrub It REAL-BROWSER proof (stage 1b evidence layer).
// Loads integration/shell-staging.html in headless Chromium (real Blink: real
// canvas, real pointer events, real rAF) and plays the speed round end-to-end:
//   swipes skipped -> tap MC answered -> Scrub doorway -> SC1 won by scrubbing
//   -> SC2 deliberately MISSED (erases the answer) -> SC3 won (hidden x2).
// Asserts: ZERO page errors / console errors, correct records, score paid.
// Screenshots land in /home/claude/proof/.  Run:
//   NODE_PATH=/home/claude/bp/node_modules node shell/browser_proof_scrub.js
"use strict";
const fs = require("fs");
const path = require("path");
const puppeteer = require("puppeteer-core");
const chromium = require("@sparticuz/chromium");

const PAGE = "file://" + path.resolve(__dirname, "../integration/shell-staging.html");
const SHOTS = "/home/claude/proof";
fs.mkdirSync(SHOTS, { recursive: true });

let fails = 0;
const check = (n, ok, d) => { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; };
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  const browser = await puppeteer.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: chromium.headless,
    defaultViewport: { width: 420, height: 900, deviceScaleFactor: 2 },
  });
  const page = await browser.newPage();

  const pageErrors = [], consoleErrors = [], netFails = [];
  page.on("pageerror", (e) => pageErrors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) consoleErrors.push(m.text()); });  // resource loads tracked via requestfailed (environmental)
  page.on("requestfailed", (r) => netFails.push(r.url().slice(0, 90)));   // environmental (fonts etc.)

  await page.goto(PAGE, { waitUntil: "load" });

  const snap = () => page.evaluate(() => ({
    screen: state.screen, idx: state.idx, recs: state.records.length, score: state.score,
    qid: (state.screen === "speed" && speedQs[state.idx]) ? speedQs[state.idx].id : null,
    hasProceed: !!document.querySelector('[onclick="transProceed()"]'),
    hasGotIt: !!document.querySelector(".cta.display"),
    flash: (document.getElementById("flash") || {}).textContent || "",
  }));
  async function until(pred, why, ms = 9000) {
    const t0 = Date.now();
    for (;;) {
      const s = await snap();
      if (pred(s)) return s;
      if (Date.now() - t0 > ms) throw new Error("timeout waiting: " + why + " :: " + JSON.stringify(s));
      await sleep(120);
    }
  }
  async function tiles() {
    return page.evaluate(() => {
      const ans = speedQs[state.idx].answer;
      return [...document.querySelectorAll("#scrubMount .er-tile")].map(t => {
        const r = t.getBoundingClientRect();
        return { opt: t.getAttribute("data-opt"), answer: t.getAttribute("data-opt") === ans,
                 x: r.left, y: r.top, w: r.width, h: r.height };
      });
    });
  }
  // one deliberate erase: down on the tile, 3 full-width passes (2 reversals), up
  async function scrubTile(t) {
    const cy = t.y + t.h / 2, x0 = t.x + 14, x1 = t.x + t.w - 14;
    await page.mouse.move(x0, cy); await page.mouse.down();
    await page.mouse.move(x1, cy, { steps: 14 });
    await page.mouse.move(x0, cy, { steps: 14 });
    await page.mouse.move(x1, cy, { steps: 14 });
    await page.mouse.up();
  }
  const shot = (name) => page.screenshot({ path: SHOTS + "/" + name });

  console.log("DRIVE: speed round");
  let guard = 0;
  for (;;) {
    if (++guard > 60) throw new Error("drive loop runaway");
    const s = await snap();

    if (s.screen === "start") { await page.click(".cta"); await until(x => x.screen !== "start", "leave start"); continue; }
    if (s.hasProceed) { await page.click('[onclick="transProceed()"]'); await sleep(250); continue; }
    if (s.hasGotIt && s.screen === "speed") { await page.click(".cta.display"); await sleep(250); continue; }

    if (s.screen === "speed") {
      const q = await page.evaluate(() => { const q = speedQs[state.idx];
        return { id: q.id, type: q.type || "mc", mode: q.mode || null, answer: String(q.answer) }; });

      if (q.type === "swipe") {                     // not today's mechanic — skip honestly
        await page.click("button.ghost");
        await until(x => x.qid !== q.id || x.hasProceed || x.screen !== "speed", "swipe skipped + advanced"); continue;
      }
      if (q.mode === "scrub") {
        const ts = await tiles();
        check(q.id + " board: 4 tiles, shuffled order served", ts.length === 4, ts.map(t => t.opt).join("|"));

        if (q.id === "SC2") {                       // deliberate MISS: erase the answer
          await scrubTile(ts.find(t => t.answer));
          await until(x => x.recs > s.recs, "SC2 miss recorded", 12000);
          await sleep(350); await shot("sc2_miss_reveal.png");
          const st = await snap();
          check("SC2 miss shows ONLY Got-it (widget already taught)", st.hasGotIt && !/answer:/i.test(st.flash), st.flash.slice(0, 60));
          await page.click(".cta.display"); await sleep(250); continue;
        }
        // WIN: erase the three wrong tiles
        const wrong = ts.filter(t => !t.answer);
        await scrubTile(wrong[0]);
        if (q.id === "SC1") await shot("sc1_mid_scrub.png");
        await scrubTile(wrong[1]); await scrubTile(wrong[2]);
        const st = await until(x => x.recs > s.recs, q.id + " win recorded", 12000);
        if (q.id === "SC1") { check("SC1 win flash paid on-screen", /Got it/.test(st.flash), st.flash.slice(0, 50)); await shot("sc1_win.png"); }
        if (q.id === "SC3") { check("SC3 hidden DOUBLE XP flash fired", /DOUBLE XP/.test(st.flash), st.flash.slice(0, 60)); await shot("sc3_x2.png");
          await until(x => x.qid !== q.id || x.screen !== "speed" || x.hasProceed, "SC3 advanced", 12000); break; }
        await until(x => x.qid !== q.id || x.screen !== "speed" || x.hasProceed, q.id + " advanced", 12000);
        continue;
      }
      // plain tap MC — answer correctly
      await page.click('.opt[data-v="' + q.answer.replace(/"/g, '\\"') + '"]');
      await until(x => x.qid !== q.id || x.hasProceed || x.screen !== "speed", q.id + " answered + advanced"); continue;
    }
    break;                                          // left the speed round
  }

  console.log("VERDICT: ledger + errors");
  const out = await page.evaluate(() => ({
    score: state.score,
    recs: state.records.filter(r => ["SC1", "SC2", "SC3"].includes(r.id)),
  }));
  const [r1, r2, r3] = ["SC1", "SC2", "SC3"].map(id => out.recs.find(r => r.id === id));
  check("SC1 win: type mc / mode scrub / pts paid", r1 && r1.ok === true && r1.type === "mc" && r1.mode === "scrub" && r1.pts > 0, r1 && "pts=" + r1.pts);
  check("SC1 telemetry: 3 eliminations, standing empty", r1 && r1.scrub && r1.scrub.eliminations.length === 3 && r1.scrub.standing.length === 0);
  check("SC1 picked = the answer", r1 && r1.picked === "Chloroplast");
  check("SC2 miss: no pay, picked null, all 3 distractors standing", r2 && r2.ok === false && r2.pts === 0 && r2.picked === null && r2.scrub.standing.length === 3 && r2.scrub.eliminations.length === 1, r2 && JSON.stringify(r2.scrub.standing));
  check("SC3 win carries x2 and doubled pts", r3 && r3.ok === true && r3.x2 === true && r3.pts > 0 && r3.pts % 2 === 0, r3 && "pts=" + r3.pts);
  check("score > 0 (the shell paid)", out.score > 0, "score=" + out.score);
  check("ZERO page errors", pageErrors.length === 0, pageErrors[0]);
  check("ZERO console errors (JS)", consoleErrors.length === 0, consoleErrors[0]);
  if (netFails.length) console.log("  note: " + netFails.length + " network fetches blocked (fonts/CDN — environmental): " + netFails[0]);

  await browser.close();
  console.log(fails ? "\nRESULT: " + fails + " FAILING" : "\nRESULT: all pass — real browser, zero JS errors");
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error("DRIVER ERROR:", e); process.exit(1); });
