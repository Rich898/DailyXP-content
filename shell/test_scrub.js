// XPDaily — Scrub It integration proof (stage 2: LIVE template wiring — merged 31 Aug 2026).
// Sources are extracted VERBATIM from shell/template_v3.html between the
// SCRUB-WIDGET / SCRUB-WIRING markers and driven with a stub DOM (house pattern,
// same as test_fx.js). Locks the HARD CONTRACT:
//   1. DELIBERATE-STROKE LAW — a stroke only erases the tile it STARTED on;
//      sweeping across other tiles does nothing to them.
//   2. Win = last one standing auto-commits -> onDone{ok:true}, full telemetry
//      (eliminations w/ hesitation, longestLived, finalTwo, standing:[]).
//   3. Erasing the ANSWER = instant miss -> onDone{ok:false}, standing carries
//      the survivors, input locks (resolving phase rejects new strokes).
//   4. Partial scrubs never heal — mask + reversals persist across strokes.
//   5. FEEDBACK-OWNERSHIP LAW — the SHELL pays on onDone (FX.celebrate + XP,
//      hidden x2 doubled, combo math identical to tap MC); no scrub source
//      contains any shake; miss pays nothing and resets combo.
//   6. LEDGER-BLINDNESS — the record keeps type:"mc"; mode:'scrub' + telemetry
//      ride alongside only.
//   7. Ratified constants — ER_TUNE {22, 0.62, 2, 2} and the block identity.
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/template_v3.html", "utf8");

let fails = 0;
function check(name, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + name + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }
function grab(startMark, endMark) {
  const m = src.match(new RegExp(startMark.replace(/[*/]/g, "\\$&") + "([\\s\\S]*?)" + endMark.replace(/[*/]/g, "\\$&")));
  if (!m) { console.error("FAIL: markers not found: " + startMark); process.exit(1); }
  return m[1];
}
const widgetSrc = grab("/*SCRUB-WIDGET-START*/", "/*SCRUB-WIDGET-END*/");
const wiringSrc = grab("/*SCRUB-WIRING-START*/", "/*SCRUB-WIRING-END*/");

// ---------------- source-level law checks ----------------------------------
console.log("SOURCE CONTRACT");
// the law is about CODE — strip comments (which document the law) before checking
const decomment = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/[^\n]*$/gm, "").replace(/([;{}])\s*\/\/[^\n]*/g, "$1");
check("widget CODE contains NO shake", !/shake|\bshk\b/i.test(decomment(widgetSrc)));
check("wiring CODE contains NO shake", !/shake|\bshk\b/i.test(decomment(wiringSrc)));
check("ratified ER_TUNE {22,0.62,2,2}", /ER_TUNE\s*=\s*\{\s*brush:22,\s*cover:0\.62,\s*revs:2,\s*crumb:2\s*\}/.test(widgetSrc));
check("block identity: label/hue/icon", /label:'Scrub It',\s*hue:'#B18CFF',\s*icon:'\\u232B'/.test(widgetSrc));
check("block identity: sub line", widgetSrc.indexOf("Rub out the wrong answers with your finger") >= 0);
check("renderSpeed routes scrub to mount", src.indexOf(`: isScrub(q)\n    ? '<div id="scrubMount"`) >= 0);
check("mount seals clock at 3rd commit", /if\(\+\+scrubCommits>=3\) clearInterval\(timer\)/.test(src));
check("timer expiry routes to finishScrub timeout", /else if\(isScrub\(tq\)\) finishScrub\(null,true\)/.test(src));
check("record keeps type:\"mc\" (ledger never learns the mode)", /type:"mc",mode:"scrub"/.test(wiringSrc));
check("shell pays via FX.celebrate on onDone", /FX\.celebrate\(fxSpec\(doubled\?3:newCombo, pts\)\)/.test(wiringSrc));

// ---------------- stub DOM -------------------------------------------------
function ctxStub() {
  const fn = () => {};
  return { save: fn, restore: fn, beginPath: fn, closePath: fn, moveTo: fn, arcTo: fn,
    arc: fn, fill: fn, stroke: fn, clearRect: fn, fillRect: fn, fillText: fn,
    setTransform: fn, setLineDash: fn, drawImage: fn, translate: fn, rotate: fn,
    measureText: (t) => ({ width: 7 * String(t).length }),
    set globalCompositeOperation(v) {}, set fillStyle(v) {}, set strokeStyle(v) {},
    set lineWidth(v) {}, set font(v) {}, set textBaseline(v) {}, set globalAlpha(v) {} };
}
function makeNode(tag) {
  const node = {
    tagName: tag, className: "", _attrs: {}, children: [], parentNode: null,
    style: {}, width: 0, height: 0, clientWidth: 0, _rect: null, _html: "",
    setAttribute(k, v) { node._attrs[k] = v; },
    getAttribute(k) { return node._attrs[k]; },
    appendChild(ch) { ch.parentNode = node; node.children.push(ch); return ch; },
    classList: {
      add(...c) { const s = new Set(node.className.split(/\s+/).filter(Boolean)); c.forEach(x => s.add(x)); node.className = [...s].join(" "); },
      remove(...c) { const s = new Set(node.className.split(/\s+/).filter(Boolean)); c.forEach(x => s.delete(x)); node.className = [...s].join(" "); },
      contains(c) { return node.className.split(/\s+/).indexOf(c) >= 0; },
    },
    _listeners: {},
    addEventListener(ev, fn) { (node._listeners[ev] = node._listeners[ev] || []).push(fn); },
    dispatch(ev, e) { (node._listeners[ev] || []).forEach(fn => fn(e)); },
    getContext() { return node._ctx || (node._ctx = ctxStub()); },
    setPointerCapture() {},
    getBoundingClientRect() { return node._rect || { left: 0, top: 0, width: 360, height: 254 }; },
    querySelector(sel) {
      const id = sel.replace("#", "");
      const walk = (n) => { if (n._attrs.id === id) return n; for (const c of n.children) { const r = walk(c); if (r) return r; } return null; };
      return walk(node);
    },
    set innerHTML(html) {
      node._html = html; node.children = [];
      // minimal parse: create a child per id="..." occurrence (erList / erResult)
      (html.match(/id="([^"]+)"/g) || []).forEach(m2 => {
        const ch = makeNode("div"); ch._attrs.id = m2.slice(4, -1);
        if (ch._attrs.id === "erList") ch.clientWidth = 360;
        node.appendChild(ch);
      });
    },
    get innerHTML() { return node._html; },
  };
  return node;
}
function makeSandbox() {
  const headKids = [];
  const doc = {
    createElement: (t) => makeNode(t),
    getElementById: (id) => headKids.find(n => n._attrs.id === id) || null,
    head: { appendChild(n) { headKids.push(n); return n; } },
  };
  const win = { devicePixelRatio: 1, matchMedia: () => ({ matches: false }) };
  return { document: doc, window: win, navigator: {},
    requestAnimationFrame: () => 0, cancelAnimationFrame: () => {} };
}
function build() {
  const sb = makeSandbox();
  const f = new Function("window", "document", "navigator", "requestAnimationFrame",
    "cancelAnimationFrame", "performance", "setTimeout",
    widgetSrc + "\n;return {mountScrub:mountScrub, ER_TUNE:ER_TUNE, SCRUB_BLOCK:SCRUB_BLOCK};");
  return f(sb.window, sb.document, sb.navigator, sb.requestAnimationFrame, sb.cancelAnimationFrame, performance, setTimeout);
}
// mount + lay out geometry: list at (0,0,360,254); tile i at y = i*66, 360x56
function mountQ(api, q, cb) {
  const container = makeNode("div");
  api.mountScrub(container, q, cb);
  const list = container.querySelector("#erList");
  list._rect = { left: 0, top: 0, width: 360, height: 254 };
  const wraps = list.children.filter(n => n.tagName === "div");
  wraps.forEach((w, i) => {
    w._rect = { left: 0, top: i * 66, width: 360, height: 56 };
    const cv = w.children[0];
    cv._rect = { left: 0, top: i * 66, width: 360, height: 56 };
  });
  return { container, list, wraps, cvs: wraps.map(w => w.children[0]) };
}
// drive one full deliberate erase on tile i: down, 3 full-width passes (2 reversals)
function eraseTile(m, i) {
  const cv = m.cvs[i], y = i * 66 + 28;
  m.list.dispatch("pointerdown", { pointerId: 1, clientX: 20, clientY: y, target: cv });
  m.list.dispatch("pointermove", { pointerId: 1, clientX: 340, clientY: y, target: cv });
  m.list.dispatch("pointermove", { pointerId: 1, clientX: 20, clientY: y, target: cv });
  m.list.dispatch("pointermove", { pointerId: 1, clientX: 340, clientY: y, target: cv });
  m.list.dispatch("pointerup", { pointerId: 1, clientX: 340, clientY: y, target: cv });
}
const Q = () => ({ type: "mc", subject: "Science", prompt: "Which organelle carries out photosynthesis?",
  options: ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"], answer: "Chloroplast",
  why: "Chloroplasts hold the chlorophyll." });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async function run() {

  // ---------------- T1: deliberate-stroke law ------------------------------
  console.log("WIDGET BEHAVIOUR");
  {
    const api = build();
    let commits = 0;
    const m = mountQ(api, Q(), { onCommit: () => commits++, onDone: () => {} });
    // stroke STARTS on tile 1 (Mitochondrion), sweeps down through tile 2 and 3 zones
    const cv1 = m.cvs[1];
    m.list.dispatch("pointerdown", { pointerId: 1, clientX: 20, clientY: 94, target: cv1 });
    m.list.dispatch("pointermove", { pointerId: 1, clientX: 340, clientY: 160, target: m.cvs[2] });
    m.list.dispatch("pointermove", { pointerId: 1, clientX: 20, clientY: 226, target: m.cvs[3] });
    m.list.dispatch("pointerup",   { pointerId: 1, clientX: 20, clientY: 226, target: m.cvs[3] });
    check("T1 sweep across tiles 2+3 commits nothing", commits === 0, "commits=" + commits);
    check("T1 tiles 2+3 untouched (no er-gone)", !m.wraps[2].classList.contains("er-gone") && !m.wraps[3].classList.contains("er-gone"));
    // and a fresh down on tile 2 still works (it was never smudged into commitment)
    eraseTile(m, 2);
    check("T1 tile 2 erases cleanly afterwards", commits === 1 && m.wraps[2].classList.contains("er-gone"));
  }

  // ---------------- T2: win path — last one standing -----------------------
  {
    const api = build();
    let commits = 0, doneRes = null;
    const m = mountQ(api, Q(), { onCommit: () => commits++, onDone: (r) => { doneRes = r; } });
    eraseTile(m, 1); eraseTile(m, 3); eraseTile(m, 2);   // erase all three distractors
    check("T2 three commits fired", commits === 3, "commits=" + commits);
    check("T2 onDone not yet (resolve window)", doneRes === null);
    await sleep(1500);                                    // winSequence fires finish at 1250ms
    check("T2 onDone ok:true", !!doneRes && doneRes.ok === true);
    const tel = doneRes && doneRes.telemetry;
    check("T2 telemetry mode:'scrub' result:'hit'", tel && tel.mode === "scrub" && tel.result === "hit");
    check("T2 eliminations order = Mito,Ribo,Nucleus",
      tel && tel.eliminations.map(e => e.opt).join("|") === "Mitochondrion|Ribosome|Nucleus");
    check("T2 hesitation: startMs <= commitMs on every erase",
      tel && tel.eliminations.every(e => Number.isFinite(e.startMs) && e.startMs <= e.commitMs));
    check("T2 longestLived = last distractor erased", tel && tel.longestLived === "Nucleus");
    check("T2 finalTwo = [Nucleus, Chloroplast]", tel && JSON.stringify(tel.finalTwo) === '["Nucleus","Chloroplast"]');
    check("T2 standing empty on a win", tel && tel.standing.length === 0);
    check("T2 widget strip = mechanic feedback w/ why", m.container.querySelector("#erResult").innerHTML.indexOf("Last one standing") >= 0);
    check("T2 survivor never got er-gone", !m.wraps[0].classList.contains("er-gone"));
  }

  // ---------------- T3: miss path — erased the answer ----------------------
  {
    const api = build();
    let doneRes = null;
    const m = mountQ(api, Q(), { onDone: (r) => { doneRes = r; } });
    eraseTile(m, 1);          // one legit elimination first
    eraseTile(m, 0);          // then erase the ANSWER
    await sleep(2200);        // missSequence: 300ms un-crumble + 1600ms read, then finish
    check("T3 onDone ok:false", !!doneRes && doneRes.ok === false);
    const tel = doneRes && doneRes.telemetry;
    check("T3 result:'miss'", tel && tel.result === "miss");
    check("T3 standing = the two surviving distractors",
      tel && tel.standing.slice().sort().join("|") === "Nucleus|Ribosome");
    check("T3 eliminations recorded up to the fatal erase",
      tel && tel.eliminations.map(e => e.opt).join("|") === "Mitochondrion|Chloroplast");
    check("T3 widget revealed answer + why in its strip",
      m.container.querySelector("#erResult").innerHTML.indexOf("That one was the answer") >= 0 &&
      m.container.querySelector("#erResult").innerHTML.indexOf("chlorophyll") >= 0);
  }

  // ---------------- T4: resolving phase locks input ------------------------
  {
    const api = build();
    let commits = 0;
    const m = mountQ(api, Q(), { onCommit: () => commits++, onDone: () => {} });
    eraseTile(m, 0);          // instant miss -> phase 'resolving'
    const before = commits;
    eraseTile(m, 2);          // try to keep scrubbing during the resolve
    check("T4 no commits accepted after resolve begins", commits === before, "commits=" + commits);
    await sleep(2100);
  }

  // ---------------- T5: partial scrubs never heal --------------------------
  {
    const api = build();
    let commits = 0;
    const m = mountQ(api, Q(), { onCommit: () => commits++, onDone: () => {} });
    // short scrub on tile 1: 2 reversals but low coverage -> no commit
    const cv = m.cvs[1];
    m.list.dispatch("pointerdown", { pointerId: 1, clientX: 20, clientY: 94, target: cv });
    m.list.dispatch("pointermove", { pointerId: 1, clientX: 80, clientY: 94, target: cv });
    m.list.dispatch("pointermove", { pointerId: 1, clientX: 20, clientY: 94, target: cv });
    m.list.dispatch("pointermove", { pointerId: 1, clientX: 80, clientY: 94, target: cv });
    m.list.dispatch("pointerup",   { pointerId: 1, clientX: 80, clientY: 94, target: cv });
    check("T5 abandoned half-scrub is legal (no commit)", commits === 0);
    // ONE later straight pass completes it: only possible if mask + reversals persisted
    m.list.dispatch("pointerdown", { pointerId: 2, clientX: 20, clientY: 94, target: cv });
    m.list.dispatch("pointermove", { pointerId: 2, clientX: 340, clientY: 94, target: cv });
    m.list.dispatch("pointerup",   { pointerId: 2, clientX: 340, clientY: 94, target: cv });
    check("T5 partial never healed — single pass finishes the erase", commits === 1 && m.wraps[1].classList.contains("er-gone"));
  }

  // ---------------- WIRING: finishScrub (the shell pays) -------------------
  console.log("WIRING BEHAVIOUR (finishScrub)");
  const constLines = [
    src.match(/var SPEED_SECONDS = [^\n]+/)[0],
    src.match(/var SPEED_BASE=[^\n]+/)[0],   // one combined line: SPEED_BASE, TIME_BONUS, COMBO_BONUS, ...
  ].join("\n");
  const x2mulSrc = (src.match(/function x2mul\([\s\S]*?\n\}/) || [""])[0];
  if (!x2mulSrc) { console.error("FAIL: x2mul not found"); process.exit(1); }

  function wire(q, stateInit) {
    const calls = { celebrate: [], tq: [], timeouts: [], score: 0 };
    const sb = {
      state: Object.assign({ combo: 0, score: 0, records: [], idx: 0 }, stateInit || {}),
      q, calls,
    };
    const prelude = `
      var answeredThis=false, timer=0, tStart=Date.now()-5000;
      var speedQs=[q];
      var T={questionDone:function(){calls.tq.push([].slice.call(arguments));}};
      var FX={celebrate:function(s){calls.celebrate.push(s);}};
      function fxSpec(c,p){return {combo:c,points:p};}
      function setScore(){calls.score=state.score;}
      function el(){return null;}
      function esc(s){return String(s);}
      function clearInterval(){}
      function setTimeout(fn,ms){calls.timeouts.push(ms);}
      function nextSpeed(){}
      function qType(q){ return (q && q.type) || "mc"; }
    `;
    const f = new Function("state", "q", "calls",
      prelude + constLines + "\n" + x2mulSrc + "\n" + wiringSrc +
      "\nreturn {finishScrub:finishScrub, isScrub:isScrub, again:function(r,t){finishScrub(r,t);}};");
    return { api: f(sb.state, q, calls), state: sb.state, calls };
  }
  const TEL = { mode: "scrub", result: "hit", totalMs: 8000,
    eliminations: [{ opt: "Mitochondrion", startMs: 900, commitMs: 2100 }],
    longestLived: "Nucleus", finalTwo: ["Nucleus", "Chloroplast"], standing: [] };

  { // W1 win pays through the shell, record is ledger-blind
    const { api, state, calls } = wire(Q(), { combo: 1, score: 100 });
    api.finishScrub({ ok: true, telemetry: TEL }, false);
    const r = state.records[0];
    check("W1 record type:'mc' + mode:'scrub'", r.type === "mc" && r.mode === "scrub");
    check("W1 picked = the answer on a win", r.picked === "Chloroplast");
    check("W1 pts paid (SPEED_BASE + time bonus + combo)", r.ok === true && r.pts > 0, "pts=" + r.pts);
    check("W1 combo advanced 1 -> 2", state.combo === 2);
    check("W1 FX.celebrate fired ONCE with the payout", calls.celebrate.length === 1 && calls.celebrate[0].points === r.pts);
    check("W1 celebrate tier = combo (not boss tier)", calls.celebrate[0].combo === 2);
    check("W1 telemetry preserved on the record", r.scrub && r.scrub.longestLived === "Nucleus" && r.scrub.finalTwo.length === 2);
    check("W1 auto-advance scheduled at 900ms", calls.timeouts[0] === 900);
    check("W1 telemetry logger got mode:'scrub'", calls.tq[0][3].mode === "scrub" && calls.tq[0][3].ok === true);
  }
  { // W2 hidden double-XP — identical to tap MC
    const q = Q(); q.x2 = true;
    const { api, state, calls } = wire(q, { combo: 0, score: 0 });
    api.finishScrub({ ok: true, telemetry: TEL }, false);
    const r = state.records[0];
    const base = r.pts / 2;
    check("W2 x2 doubles the payout", r.x2 === true && Number.isInteger(base) && base > 0, "pts=" + r.pts);
    check("W2 celebrate at showcase tier 3", calls.celebrate[0].combo === 3);
    check("W2 doubled advance window 1400ms", calls.timeouts[0] === 1400);
  }
  { // W3 miss: no pay, combo resets, telemetry kept
    const missTel = Object.assign({}, TEL, { result: "miss", standing: ["Nucleus", "Ribosome"] });
    const { api, state, calls } = wire(Q(), { combo: 4, score: 500 });
    api.finishScrub({ ok: false, telemetry: missTel }, false);
    const r = state.records[0];
    check("W3 miss pays nothing", r.ok === false && r.pts === 0 && state.score === 500);
    check("W3 combo resets to 0", state.combo === 0);
    check("W3 celebrate NOT fired on a miss", calls.celebrate.length === 0);
    check("W3 picked null (no option chosen on a scrub miss)", r.picked === null);
    check("W3 standing distractors preserved", r.scrub.standing.join("|") === "Nucleus|Ribosome");
  }
  { // W4 timeout: miss record, no telemetry subobject, no pay
    const { api, state, calls } = wire(Q(), { combo: 2, score: 300 });
    api.finishScrub(null, true);
    const r = state.records[0];
    check("W4 timeout records a miss", r.ok === false && r.pts === 0 && r.mode === "scrub");
    check("W4 no scrub telemetry on a timeout", !("scrub" in r));
    check("W4 celebrate silent on timeout", calls.celebrate.length === 0);
  }
  { // W5 idempotency — onDone after timeout (the race) cannot double-record
    const { api, state } = wire(Q(), {});
    api.finishScrub(null, true);
    api.again({ ok: true, telemetry: TEL }, false);
    check("W5 answeredThis guards the race (1 record)", state.records.length === 1 && state.records[0].ok === false);
  }
  { // W6 isScrub gate
    const { api } = wire(Q(), {});
    check("W6 isScrub true only for mc+mode:'scrub'",
      api.isScrub({ type: "mc", mode: "scrub" }) === true &&
      api.isScrub({ type: "mc" }) === false &&
      api.isScrub({ type: "swipe", mode: "scrub" }) === false);
  }

  console.log(fails ? "\nRESULT: " + fails + " FAILING" : "\nRESULT: all pass");
  process.exit(fails ? 1 : 0);
})();
