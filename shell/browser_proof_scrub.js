// XPDaily — LIVE-SHELL real-browser proof (Scrub It + numeric decimal/fraction).
// Stage 2 (31 Aug 2026): the scrub widget is MERGED into shell/template_v3.html, so this
// proof now stamps a build of THE LIVE TEMPLATE, serves it a fixture quiz shaped like the
// live sets (Quick Recall -> Scrub It block -> Numeric steady), and plays it end-to-end
// in headless Chromium (real Blink: real canvas, real pointer events, real rAF):
//   recall answered -> Scrub doorway -> S2 WON by erasing all three distractors
//   -> S3 deliberately MISSED (erases the answer) -> Numeric doorway
//   -> T1 MENTAL pad types 0.4 (the exact answer t1 could not enter on 31 Aug)
//   -> T2 CALC pad writes the fraction 2/5 with the a/b key (frac reveal form).
// Asserts: ZERO page errors / console errors, correct records, XP paid, usedCalc honest.
// Screenshots land in $XP_PROOF_DIR (default: shell/proof/, gitignored).
// Run:  node shell/browser_proof_scrub.js
//   (playwright resolved from the local install or NODE_PATH; Chromium from
//    PLAYWRIGHT_BROWSERS_PATH or the playwright default.)
"use strict";
const fs = require("fs");
const path = require("path");

function req(mod) {
  try { return require(mod); } catch (e) {
    const roots = [process.env.NODE_PATH, "/opt/node22/lib/node_modules", "/usr/lib/node_modules"].filter(Boolean);
    for (const r of roots) { try { return require(path.join(r, mod)); } catch (e2) {} }
    throw e;
  }
}
const { chromium } = req("playwright");

const SHOTS = process.env.XP_PROOF_DIR || path.join(__dirname, "proof");
fs.mkdirSync(SHOTS, { recursive: true });

let fails = 0;
const check = (n, ok, d) => { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; };
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// ---- stamp a build of the LIVE template (test seat: ingest drops SYSTEM-TEST rows) ----
const BUILD = path.join(__dirname, "testbuild");
fs.mkdirSync(BUILD, { recursive: true });
const stamped = fs.readFileSync(path.join(__dirname, "template_v3.html"), "utf8")
  .replace(/__STUDENT__/g, "SYSTEM-TEST").replace(/__NAME__/g, "Proof Seat");
const PAGE_FILE = path.join(BUILD, "proofbuild.html");
fs.writeFileSync(PAGE_FILE, stamped);
const PAGE = "file://" + PAGE_FILE;

// ---- fixture quiz, shaped like the live sets ----
const SCRUB_BLOCK = { label: "Scrub It", hue: "#B18CFF", icon: "⌫", sub: "Rub out the wrong answers with your finger", cta: "Start scrubbing →" };
const NUM_BLOCK = { label: "Numeric", hue: "#14C7C7", icon: "#", sub: "Type the answer", cta: "Start →" };
const FIX = {
  student: "SYSTEM-TEST", date: "2026-08-31", day: "MON", tag: "PROOF", title: "proof",
  questions: [
    { id: "S1", phase: "speed", subject: "English", block: { label: "Quick Recall", hue: "#16E08C", icon: "●", sub: "Four options, one answer", cta: "Keep going →" },
      prompt: "Who wrote Romeo and Juliet?", options: ["Shakespeare", "Marlowe", "Dickens", "Austen"], answer: "Shakespeare", why: "Shakespeare.", fresh: true },
    { id: "S2", phase: "speed", subject: "History", block: SCRUB_BLOCK, mode: "scrub",
      prompt: "Which empire built the Colosseum?", options: ["Roman Empire", "Ottoman Empire", "Persian Empire", "Mongol Empire"], answer: "Roman Empire", why: "Rome — opened 80 AD.", fresh: true },
    { id: "S3", phase: "speed", subject: "Science", block: SCRUB_BLOCK, mode: "scrub",
      prompt: "Which organelle carries out photosynthesis?", options: ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"], answer: "Chloroplast", why: "Chlorophyll lives there.", fresh: true },
    { id: "T1", phase: "steady", subject: "Maths", block: NUM_BLOCK, type: "numeric",
      prompt: "The probability of green is 0.6. What is the probability of NOT green?", answer: 0.4, calc: false, pre: "", post: "", why: "1 − 0.6 = 0.4.", fresh: true },
    { id: "T2", phase: "steady", subject: "Maths", block: NUM_BLOCK, type: "numeric",
      prompt: "A bag has 4 yellow and 6 green counters. What is the probability of yellow?", answer: 0.4, calc: true, frac: "2/5", pre: "", post: "", why: "4 of 10 = 2/5.", fresh: true },
    { id: "TB1", phase: "teach", subject: "Science", prompt: "Explain photosynthesis in your own words." },
  ],
};

(async () => {
  const browser = await chromium.launch({ args: ["--force-prefers-reduced-motion=no"] });
  const page = await browser.newPage({ viewport: { width: 420, height: 900 }, deviceScaleFactor: 2 });

  const pageErrors = [], consoleErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e)));
  page.on("console", (m) => {
    if (m.type() === "error" && !/Failed to load resource|net::|ERR_/.test(m.text())) consoleErrors.push(m.text());
  });
  await page.route("**raw.githubusercontent.com**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FIX) }));
  // never let the proof touch live sinks (it stops before submit; belt and braces)
  await page.route("**script.google.com**", (r) => r.abort());
  await page.route("**supabase.co**", (r) => r.abort());

  const shot = (n) => page.screenshot({ path: path.join(SHOTS, n + ".png") });

  // one deliberate erase: down on the tile, three full-width passes (>=2 reversals)
  async function scrubTile(optLabel) {
    const tile = page.locator('.er-tile[data-opt="' + optLabel + '"] canvas');
    const b = await tile.boundingBox();
    const y = b.y + b.height / 2, x0 = b.x + 8, x1 = b.x + b.width - 8;
    await page.mouse.move(x0, y);
    await page.mouse.down();
    await page.mouse.move(x1, y, { steps: 16 });
    await page.mouse.move(x0, y, { steps: 16 });
    await page.mouse.move(x1, y, { steps: 16 });
    await page.mouse.up();
  }

  console.log("LIVE TEMPLATE PLAY-THROUGH");
  await page.goto(PAGE);
  await page.waitForSelector("text=Drop in", { timeout: 15000 });
  check("start screen rendered from injected quiz", true);
  await shot("01-start");
  await page.click("button:has-text('Drop in')");

  // Quick Recall doorway -> S1
  await page.waitForSelector(".tcard:has-text('Quick Recall')");
  await page.click(".tcont");
  await page.waitForSelector('.opt[data-v="Shakespeare"]');
  await page.click('.opt[data-v="Shakespeare"]');
  await page.waitForSelector(".flash.ok");

  // Scrub It doorway (the violet card Rich saw — now it must play as SCRUB, not MC)
  await page.waitForSelector(".tcard:has-text('Scrub It')", { timeout: 8000 });
  check("Scrub It doorway card shows", true);
  await shot("02-scrub-doorway");
  await page.click(".tcont");

  // S2 — WIN: canvases mounted (not tappable MC buttons), erase all three distractors
  await page.waitForSelector("#scrubMount .er-tile canvas");
  const tiles = await page.locator(".er-tile").count();
  const optBtns = await page.locator(".opt").count();
  check("S2 mounts 4 scrub TILES, zero MC option buttons", tiles === 4 && optBtns === 0, "tiles=" + tiles + " opts=" + optBtns);
  await shot("03-scrub-live");
  await scrubTile("Ottoman Empire");
  await page.waitForSelector('.er-tile[data-opt="Ottoman Empire"].er-gone');
  check("S2 first distractor crumbles (shards break)", true);
  await scrubTile("Persian Empire");
  await scrubTile("Mongol Empire");
  await page.waitForSelector(".er-strip.ok:has-text('Last one standing')", { timeout: 5000 });
  check("S2 survivor auto-commits — 'Last one standing'", true);
  await shot("04-scrub-win");
  await page.waitForSelector(".flash.ok", { timeout: 5000 });
  check("S2 shell pays the win (flash + XP)", true);

  // S3 — MISS: erasing the ANSWER resolves instantly against you
  await page.waitForSelector("#scrubMount .er-tile canvas", { timeout: 8000 });
  await scrubTile("Mitochondrion");
  await scrubTile("Chloroplast");   // the answer — instant miss
  await page.waitForSelector(".er-strip.bad:has-text('That one was the answer')", { timeout: 5000 });
  check("S3 answer-erase = instant miss, green un-crumble strip", true);
  await shot("05-scrub-miss");
  await page.waitForSelector("#flash button:has-text('Got it')", { timeout: 6000 });
  await page.click("#flash button:has-text('Got it')");

  // Numeric doorway -> T1 MENTAL: type 0.4 (the 31 Aug live-fire case)
  await page.waitForSelector(".tcard:has-text('Numeric')", { timeout: 8000 });
  await page.click(".tcont");
  await page.waitForSelector(".nm-pad.num");
  const mentalKeys = await page.locator(".nm-pad.num .nm-key").allTextContents();
  check("T1 mental pad carries . and a/b keys", mentalKeys.indexOf(".") >= 0 && mentalKeys.indexOf("a/b") >= 0, mentalKeys.join(","));
  await shot("06-mental-pad");
  await page.click('.nm-key[data-k="0"]');
  await page.click('.nm-key[data-k="."]');
  await page.click('.nm-key[data-k="4"]');
  await page.click("#nmSubmit");
  await page.waitForSelector(".nm-strip.ok", { timeout: 5000 });
  check("T1 mental 0.4 accepted (was unanswerable live)", true);
  await shot("07-mental-decimal-correct");

  // T2 CALC: write the fraction 2/5 with the a/b key; reveal shows the frac form
  await page.waitForSelector(".nm-pad.calc", { timeout: 8000 });
  await page.click('.nm-key[data-k="2"]');
  await page.click('.nm-key[data-k="/"]');
  await page.click('.nm-key[data-k="5"]');
  await shot("08-calc-fraction-entry");
  await page.click("#nmSubmit");
  await page.waitForSelector(".nm-strip.ok", { timeout: 5000 });
  const strip = await page.locator(".nm-strip.ok").innerText();
  check("T2 fraction 2/5 accepted; reveal shows '2/5 (= 0.4)'", strip.indexOf("2/5 (= 0.4)") >= 0, strip.slice(0, 80));
  await shot("09-calc-fraction-correct");

  // teach-back doorway = end of the proof path
  await page.waitForSelector(".tcard:has-text('Teach-back')", { timeout: 8000 });
  check("run reaches the teach-back doorway", true);

  // ---- records: the ledger-facing truth ----
  const rec = await page.evaluate(() => window.state.records);
  const byId = {}; rec.forEach(r => byId[r.id] = r);
  check("records: S2 type:'mc' mode:'scrub' ok:true, XP paid", byId.S2 && byId.S2.type === "mc" && byId.S2.mode === "scrub" && byId.S2.ok === true && byId.S2.pts > 0, JSON.stringify(byId.S2));
  check("records: S2 carries scrub telemetry (eliminations, finalTwo)", byId.S2 && byId.S2.scrub && byId.S2.scrub.eliminations.length === 3 && byId.S2.scrub.finalTwo.length === 2);
  check("records: S3 scrub miss, no pay, standing distractors", byId.S3 && byId.S3.ok === false && byId.S3.pts === 0 && byId.S3.scrub.standing.length === 2, JSON.stringify(byId.S3 && byId.S3.scrub));
  check("records: T1 numeric ok, value 0.4, usedCalc:false", byId.T1 && byId.T1.ok === true && byId.T1.value === 0.4 && byId.T1.usedCalc === false, JSON.stringify(byId.T1));
  check("records: T2 numeric ok via fraction, usedCalc:false (a/b is not calculator use)", byId.T2 && byId.T2.ok === true && byId.T2.usedCalc === false, JSON.stringify(byId.T2));

  check("ZERO page errors", pageErrors.length === 0, pageErrors.join(" | ").slice(0, 200));
  check("ZERO console errors", consoleErrors.length === 0, consoleErrors.join(" | ").slice(0, 200));

  await browser.close();
  console.log(fails ? "\nRESULT: " + fails + " FAILING" : "\nRESULT: all pass — screenshots in " + SHOTS);
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error("PROOF CRASHED:", e); process.exit(1); });
