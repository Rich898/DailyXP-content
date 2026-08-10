// DailyXP v3.0 — full-shell integration test.
// Loads the REAL built shell (testbuild/index.html) in jsdom, stubs the network
// (questions come from the actual y9.json TEST file that will be
// published; the webhook captures what would hit the Google Sheet),
// then plays a complete run by clicking through the DOM:
//   speed Q1 correct → speed Q2 WRONG (reveal path) → steady picked+
//   confidence+lock → teach-back typed → done screen → auto-submit.
// Asserts the captured payload is complete and the timing invariant holds.
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");
const TESTQUIZ = JSON.parse(fs.readFileSync(__dirname + "/y9.json", "utf8"));

let webhookBody = null;
let webhookContentType = null;
let questionsRequested = null;

const dom = new JSDOM(html, {
  url: "https://xpdaily-test.netlify.test/",
  runScripts: "dangerously",
  pretendToBeVisual: true,
  beforeParse(window) {
    window.fetch = function (url, opts) {
      url = String(url);
      if (url.indexOf("raw.githubusercontent.com") !== -1) {
        questionsRequested = url;
        return Promise.resolve({ ok: true, json: () => Promise.resolve(TESTQUIZ) });
      }
      if (url.indexOf("script.google.com") !== -1) {
        webhookBody = opts && opts.body;
        webhookContentType = opts && opts.headers && opts.headers["Content-Type"];
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) });
      }
      return Promise.reject(new Error("unexpected fetch: " + url));
    };
  },
});

const { window } = dom;
const { document } = window;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function buttons() { return Array.from(document.querySelectorAll("button")); }
function clickByText(txt) {
  const b = buttons().find((x) => x.textContent.indexOf(txt) !== -1 && !x.disabled);
  if (!b) throw new Error("no clickable button containing: " + txt + " | have: " + buttons().map((x) => x.textContent.trim().slice(0, 30)).join(" / "));
  b.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
}
function clickOption(value) {
  const b = buttons().find((x) => x.classList.contains("opt") && x.getAttribute("data-v") === value && !x.disabled);
  if (!b) throw new Error("no option: " + value);
  b.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
}
function stage() { return document.getElementById("stage").textContent; }

const checks = [];
function check(name, cond, detail) { checks.push([name, cond, detail]); if (!cond) console.error("FAIL:", name, detail || ""); }

(async () => {
  await sleep(80); // boot + stubbed fetch resolve
  check("questions fetched from GitHub raw with cache-buster",
    !!questionsRequested && questionsRequested.indexOf("y9.json?t=") !== -1, questionsRequested);
  check("start screen rendered from remote data", stage().indexOf("Tonight's run") !== -1 && stage().indexOf("4 questions") !== -1, stage().slice(0, 80));
  check("start screen shows quiz-provided day/tag, not device date",
    stage().indexOf("TEST SUN 2 AUG 2026") !== -1 && stage().indexOf("SYSTEM TEST") !== -1);

  clickByText("Drop in");
  await sleep(30);

  // SPEED Q1 — answer correctly after ~1.2s of "thinking"
  check("speed Q1 up", stage().indexOf("7 × 8") !== -1);
  await sleep(1200);
  clickOption("56");
  await sleep(1100); // 900ms auto-advance

  // SPEED Q2 — answer WRONG, read reveal ~1.5s, then advance
  check("speed Q2 up", stage().indexOf("closest to the Sun") !== -1);
  await sleep(800);
  clickOption("Venus");
  await sleep(50);
  check("wrong answer shows the why", stage().indexOf("Mercury — closest in") !== -1);
  await sleep(1500); // reveal-reading time → must land in idle
  clickByText("Got it");
  await sleep(30);

  // STEADY — pick, confidence, re-renders must not restart the clock
  check("steady up, no clock", stage().indexOf("NO CLOCK") !== -1);
  await sleep(900);
  clickOption("Experience Points");
  await sleep(300);
  clickByText("Sure");
  await sleep(300);
  clickByText("Lock it in");
  await sleep(50);
  check("steady reveal shows points", stage().indexOf("+250") !== -1);
  clickByText("Next");
  await sleep(30);

  // TEACH-BACK — type 90 chars, send
  check("teach-back up", stage().indexOf("SYSTEM TEST: type any 80+") !== -1);
  const tb = document.getElementById("tb");
  tb.value = "x".repeat(90);
  tb.dispatchEvent(new window.Event("input", { bubbles: true }));
  await sleep(600);
  clickByText("Send it");
  await sleep(150); // done screen + autoSubmit fires

  check("done screen rendered", stage().indexOf("FULL TIME") !== -1);
  check("webhook received a POST", webhookBody !== null);
  check("POST is a CORS-simple request (text/plain)", String(webhookContentType).indexOf("text/plain") === 0, webhookContentType);
  const sendStat = document.getElementById("sendStat");
  check("kid sees the sent confirmation", !!sendStat && sendStat.textContent.indexOf("uploaded to the Vault") !== -1, sendStat && sendStat.textContent);

  const p = JSON.parse(webhookBody);
  check("payload: student/name/date/tag", p.student === "y9" && p.name === "Tester" && p.date === "2026-08-02" && p.tag === "SYSTEM TEST");
  check("payload: score positive, max present", p.score > 0 && p.maxScore > 0, p.score + "/" + p.maxScore);
  check("payload: speed 1/2, steady 1/1, teach done",
    p.speed.right === 1 && p.speed.of === 2 && p.steady.right === 1 && p.steady.of === 1 && p.teach.done === true,
    JSON.stringify({ speed: p.speed, steady: p.steady }));
  check("payload: 4 records incl. teach text", p.records.length === 4 && p.records[3].text.length === 90);
  check("payload: steady confidence captured", p.records[2].confidence === "Sure");
  check("payload: per-question timing for all 4", p.timing.perQuestion.length === 4);
  check("payload: THE invariant — active ≤ elapsed", p.timing.activeSecs <= p.timing.elapsedSecs,
    p.timing.activeSecs + " vs " + p.timing.elapsedSecs);
  check("payload: idle > 0 (reveal-reading etc. no longer counted as active)", p.timing.idleSecs > 0, p.timing.idleSecs);
  check("payload: summaryText present with honest timing line", p.summaryText.indexOf("Active time") !== -1 && p.summaryText.indexOf("Elapsed") !== -1);
  check("payload: attempt counter present", p.attempt >= 1 && p.attemptsAllTime >= 1, p.attempt + "/" + p.attemptsAllTime);

  console.log("─".repeat(64));
  console.log("Captured run: score " + p.score + "/" + p.maxScore +
    " · active " + p.timing.activeSecs + "s · elapsed " + p.timing.elapsedSecs + "s · idle " + p.timing.idleSecs + "s");
  console.log("Per-question secs: " + p.timing.perQuestion.map((q) => q.id + " " + q.secs + "s").join(" · "));
  console.log("─".repeat(64));
  checks.forEach((c) => console.log((c[1] ? "  PASS  " : "  FAIL  ") + c[0]));
  console.log("─".repeat(64));
  const failed = checks.filter((c) => !c[1]);
  if (failed.length) { console.error(failed.length + " FAILURES"); process.exit(1); }
  console.log("FULL-RUN INTEGRATION: ALL " + checks.length + " CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
