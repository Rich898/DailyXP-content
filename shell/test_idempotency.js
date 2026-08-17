// XPDaily v3.1 — submit idempotency proof.
// Proves the payload carries a STABLE per-run id (reused across builds → the offline outbox flush
// re-sends the same id, which the DB unique index dedupes), and that autoSubmit's within-session
// guard fires the webhook exactly once even if called again.
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

const FIX = {
  student: "y9", date: "2026-08-02", day: "TEST", dateLabel: "SUN 2 AUG 2026", tag: "SYSTEM TEST", title: "idem test",
  questions: [
    { id: "S1", phase: "speed", subject: "Maths", prompt: "2 + 2?", options: ["3", "4"], answer: "4", why: "Four.", fresh: true },
    { id: "T1", phase: "steady", subject: "Gaming", prompt: "XP stands for?", options: ["Extra Power", "Experience Points"], answer: "Experience Points", why: "XP.", fresh: true },
    { id: "TB", phase: "teach", subject: "Science", prompt: "SYSTEM TEST: type any 80+ character explanation." }
  ]
};

let webhookHits = 0, supabaseHits = 0; const webhookBodies = [];
const dom = new JSDOM(src, {
  url: "https://xpdaily-test.netlify.test/", runScripts: "dangerously", pretendToBeVisual: true,
  beforeParse(window) {
    window.fetch = function (url, opts) {
      url = String(url);
      if (url.indexOf("raw.githubusercontent.com") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve(FIX) });
      if (url.indexOf("/functions/v1/grade-teachback") !== -1) return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
      if (url.indexOf("/rest/v1/runs_raw") !== -1) { supabaseHits++; return Promise.resolve({ ok: true, json: () => Promise.resolve({}) }); }
      if (url.indexOf("script.google.com") !== -1) { webhookHits++; webhookBodies.push(opts && opts.body); return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); }
      return Promise.reject(new Error("unexpected fetch: " + url));
    };
  },
});
const { window } = dom; const { document } = window;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const btns = () => Array.from(document.querySelectorAll("button"));
const ct = (t) => { const b = btns().find((x) => x.textContent.indexOf(t) !== -1 && !x.disabled); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };
const opt = (v) => { const b = btns().find((x) => x.classList.contains("opt") && x.getAttribute("data-v") === v); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };

(async () => {
  console.log("submit idempotency:");
  await sleep(80);
  ct("Drop in"); await sleep(30);
  opt("4"); await sleep(1000);
  opt("Experience Points"); await sleep(30); ct("Sure"); await sleep(30); ct("Lock it in"); await sleep(30); ct("Next"); await sleep(30);
  const tb = document.getElementById("tb"); tb.value = "Respiration releases energy from glucose in every living cell, not only in plants, which is why all organisms need it."; tb.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(40);
  ct("Send it"); await sleep(150);

  check("webhook fired exactly once", webhookHits === 1, "hits=" + webhookHits);
  check("supabase mirror fired exactly once", supabaseHits === 1, "hits=" + supabaseHits);
  const p1 = JSON.parse(webhookBodies[0]);
  check("payload carries a non-empty runId", typeof p1.runId === "string" && p1.runId.length > 5, String(p1.runId));

  // re-fire autoSubmit → the within-session guard must prevent a second webhook POST
  window.autoSubmit();
  await sleep(50);
  check("re-calling autoSubmit does NOT submit again (guard holds)", webhookHits === 1, "hits=" + webhookHits);

  // rebuilding the payload returns the SAME runId (so an outbox retry dedupes)
  const p2 = window.buildPayload();
  check("runId is stable across rebuilds (outbox retry dedupes)", p2.runId === p1.runId, p2.runId + " vs " + p1.runId);

  console.log("─".repeat(60));
  if (fails) { console.error(fails + " FAILURES"); process.exit(1); }
  console.log("SUBMIT IDEMPOTENCY: ALL CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
