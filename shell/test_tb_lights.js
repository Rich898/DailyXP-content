// XPDaily v3.1 — teach-back lights (live grading) proof.
// Drives a full run to the done screen; stubs the Supabase grading endpoint. Proves: an instant
// "marking…" state, then three coaching lights (accuracy/spelling/punctuation) render from the
// endpoint reply, and that a FAILED endpoint degrades silently (no lights) without breaking the run.
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

const FIX = {
  student: "y9", date: "2026-08-02", day: "TEST", dateLabel: "SUN 2 AUG 2026", tag: "SYSTEM TEST", title: "tb test",
  questions: [
    { id: "S1", phase: "speed", subject: "Maths", prompt: "2 + 2?", options: ["3", "4"], answer: "4", why: "Four.", fresh: true },
    { id: "T1", phase: "steady", subject: "Gaming", prompt: "XP stands for?", options: ["Extra Power", "Experience Points"], answer: "Experience Points", why: "XP.", fresh: true },
    { id: "TB", phase: "teach", subject: "Science", prompt: "SYSTEM TEST: type any 80+ character explanation." }
  ]
};

// Run the full flow; `gradeResponder` decides what the grading endpoint returns.
async function runFlow(gradeResponder) {
  let markingSeen = false;
  const dom = new JSDOM(src, {
    url: "https://xpdaily-test.netlify.test/", runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = function (url, opts) {
        url = String(url);
        if (url.indexOf("raw.githubusercontent.com") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve(FIX) });
        if (url.indexOf("/functions/v1/grade-teachback") !== -1) return gradeResponder();
        if (url.indexOf("/rest/v1/runs_raw") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
        if (url.indexOf("script.google.com") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) });
        return Promise.reject(new Error("unexpected fetch: " + url));
      };
    },
  });
  const { window } = dom; const { document } = window;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const btns = () => Array.from(document.querySelectorAll("button"));
  const ct = (t) => { const b = btns().find((x) => x.textContent.indexOf(t) !== -1 && !x.disabled); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };
  const opt = (v) => { const b = btns().find((x) => x.classList.contains("opt") && x.getAttribute("data-v") === v); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };

  await sleep(80);
  ct("Drop in"); await sleep(30);
  opt("4"); await sleep(950);
  opt("Experience Points"); await sleep(30); ct("Sure"); await sleep(30); ct("Lock it in"); await sleep(30); ct("Next"); await sleep(30);
  const tb = document.getElementById("tb"); tb.value = "Respiration releases energy from glucose in every living cell, not only in plants, which is why all organisms need it."; tb.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(40);
  ct("Send it");
  await sleep(5);
  const lightsNow = document.getElementById("tbLights");
  markingSeen = !!(lightsNow && lightsNow.textContent.indexOf("Marking") !== -1);
  await sleep(150); // let the grade resolve
  const box = document.getElementById("tbLights");
  return { markingSeen, cells: box ? Array.from(box.querySelectorAll(".tbl")) : [], html: box ? box.innerHTML : "" };
}

(async () => {
  console.log("teach-back lights:");

  // SUCCESS: endpoint returns solid / amber / green (resolves after a beat so 'Marking…' is observable)
  const okResp = () => new Promise((res) => setTimeout(() => res({ ok: true, json: () => Promise.resolve({ verdict: "solid", depth: "connects", spelling: "amber", punctuation: "green", reason: "clear." }) }), 40));
  const s = await runFlow(okResp);
  check("shows 'Marking…' immediately on submit", s.markingSeen);
  check("renders three lights once graded", s.cells.length === 3, String(s.cells.length));
  if (s.cells.length === 3) {
    const cls = s.cells.map((c) => (c.className.match(/tbl (green|amber|red)/) || [])[1]);
    const labels = s.cells.map((c) => c.querySelector(".lb").textContent);
    check("accuracy=green (solid), spelling=amber, punctuation=green", cls[0] === "green" && cls[1] === "amber" && cls[2] === "green", cls.join(","));
    check("labels are Accuracy / Spelling / Punctuation", labels[0] === "Accuracy" && labels[1] === "Spelling" && labels[2] === "Punctuation", labels.join(","));
    check("green shows tick, amber shows dot", s.cells[0].querySelector(".g").textContent === "\u2713" && s.cells[1].querySelector(".g").textContent === "\u25CF");
  }

  // FAILURE: endpoint 500s → silent, no lights, run intact
  const badResp = () => Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({ error: "x" }) });
  const f = await runFlow(badResp);
  check("endpoint failure → no lights (silent, coaching lands in wrap)", f.cells.length === 0 && f.html.trim() === "", f.html.slice(0, 40));

  console.log("─".repeat(60));
  if (fails) { console.error(fails + " FAILURES"); process.exit(1); }
  console.log("TEACH-BACK LIGHTS: ALL CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
