// XPDaily — FX-core proof.
// The FX functions are extracted VERBATIM from the built shell (between the
// FX-CORE markers) and driven with a tiny stub DOM. Locks the HARD CONTRACT:
//   1. Pooled + capped — never exceeds MAX_PARTICLES no matter how hard it's hit,
//      and every spawned node is cleaned up (live returns to 0).
//   2. reduce-motion — burst/flash/kick are suppressed; number-pop still renders.
//   3. Escalation tiers — a plain correct answer is quiet; combos escalate; the
//      boss finisher is the loudest.
//   4. THE LAW — the FX-CORE source contains NO reference to game state
//      (state., score, combo writes, records, T.questionDone, timing). It can
//      only decorate. This is what guarantees juice can never corrupt the ledger.
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");
const m = src.match(/\/\*FX-CORE-START\*\/([\s\S]*?)\/\*FX-CORE-END\*\//);
if (!m) { console.error("FAIL: fx core not found in built shell"); process.exit(1); }
const fxSource = m[1];

let fails = 0;
function check(name, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + name + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

// ---- tiny stub DOM (no jsdom needed) -------------------------------------
function makeStubDoc() {
  const listeners = [];
  function makeNode(tag) {
    const style = {}; 
    const node = {
      tagName: tag, className: "", textContent: "", parentNode: null,
      children: [], style: { setProperty: (k, v) => { style[k] = v; }, _v: style },
      offsetWidth: 1,
      classList: {
        add(...c) { const s = new Set(node.className.split(/\s+/).filter(Boolean)); c.forEach(x => s.add(x)); node.className = [...s].join(" "); },
        remove(...c) { const s = new Set(node.className.split(/\s+/).filter(Boolean)); c.forEach(x => s.delete(x)); node.className = [...s].join(" "); },
        contains(c) { return node.className.split(/\s+/).indexOf(c) >= 0; },
      },
      appendChild(ch) { ch.parentNode = node; node.children.push(ch); return ch; },
      removeChild(ch) { const i = node.children.indexOf(ch); if (i >= 0) node.children.splice(i, 1); ch.parentNode = null; return ch; },
      addEventListener(ev, fn, o) { listeners.push({ node, ev, fn, once: o && o.once }); },
      removeEventListener() {},
      getBoundingClientRect() { return { width: 380, height: 700 }; },
    };
    return node;
  }
  const fxroot = makeNode("div"); fxroot.id = "fxroot";
  const wrap = makeNode("div"); wrap.className = "wrap";
  const doc = {
    _fxroot: fxroot, _wrap: wrap, _listeners: listeners,
    getElementById: (id) => (id === "fxroot" ? fxroot : null),
    querySelector: (sel) => (sel === ".wrap" ? wrap : null),
    body: makeNode("body"),
    createElement: (t) => makeNode(t),
  };
  // fire all pending animationend listeners (simulates animations completing)
  doc._finishAnimations = () => {
    const pending = listeners.filter(l => l.ev === "animationend");
    pending.forEach(l => { try { l.fn(); } catch (e) {} });
  };
  return doc;
}

function build(reduceMotion) {
  const doc = makeStubDoc();
  const factory = new Function("opts", fxSource + "; return makeFX(opts);");
  const fx = factory({ document: doc, reduceMotion: () => reduceMotion });
  return { doc, fx };
}

// ---- 1. pooling + hard cap ----------------------------------------------
console.log("pooling + cap");
{
  const { doc, fx } = build(false);
  // hammer it far past the cap in one frame
  for (let i = 0; i < 20; i++) fx.burst(100, 100, ["#f00"], 50);
  const spawned = doc._fxroot.children.length;
  check("never exceeds the 60-particle cap under a flood", spawned <= 60, "spawned=" + spawned);
  check("live count tracks spawned nodes", fx._live() === spawned, "live=" + fx._live());
  doc._finishAnimations();
  check("all particles cleaned up after animations end (no leak)", doc._fxroot.children.length === 0 && fx._live() === 0, "left=" + doc._fxroot.children.length);
}

// ---- 2. reduced motion ---------------------------------------------------
console.log("reduced motion");
{
  const { doc, fx } = build(true);
  const b = fx.burst(100, 100, ["#f00"], 20);
  const fl = fx.flash("rgba(0,0,0,.5)");
  const k = fx.kick(3);
  check("burst suppressed under reduce-motion", b === 0 && doc._fxroot.children.length === 0);
  check("flash suppressed under reduce-motion", fl === false);
  check("kick (shake) suppressed under reduce-motion", k === false);
  const p = fx.popNumber(100, 100, "+250", "#f00");
  check("number-pop STILL renders under reduce-motion (gentle fade in CSS)", p === true && doc._fxroot.children.length === 1);
}

// ---- 3. escalation tiers -------------------------------------------------
console.log("escalation (quiet floor -> louder when earned)");
function loudness(spec) {
  const { doc, fx } = build(false);
  fx.celebrate(spec);
  const wrapKick = doc._wrap.className.match(/kick(\d)/);
  return { particles: doc._fxroot.children.filter(n => n.className.indexOf("fxparticle") >= 0).length,
           flash: doc._fxroot.children.some(n => n.className.indexOf("fxflash") >= 0),
           kick: wrapKick ? +wrapKick[1] : 0 };
}
// amp+intense amplification: same combo -> louder + flashes earlier than baseline
function loudnessSpec(spec){
  const { doc, fx } = build(false); fx.celebrate(spec);
  const wk = doc._wrap.className.match(/kick(\d)/);
  return { particles: doc._fxroot.children.filter(n=>n.className.indexOf("fxparticle")>=0).length,
           flash: doc._fxroot.children.some(n=>n.className.indexOf("fxflash")>=0),
           kick: wk?+wk[1]:0 };
}
const l1 = loudness({ combo: 1, points: 100, palette: null });
const l2 = loudness({ combo: 2, points: 100, palette: null });
const l3 = loudness({ combo: 3, points: 100, palette: null });
const l4 = loudness({ combo: 5, points: 100, palette: null });
const lb = loudness({ boss: true, points: 250, palette: null });
check("plain correct (combo 1) now gives a real small burst (noticeable floor)", l1.particles >= 8 && !l1.flash, JSON.stringify(l1));
check("combo 2 escalates above the floor", l2.particles > l1.particles && l2.kick >= 2, JSON.stringify(l2));
check("combo 3 builds further + flashes", l3.particles > l2.particles && l3.flash === true && l3.kick === 3, JSON.stringify(l3));
check("combo 4+ is big (flash + heavy burst)", l4.flash === true && l4.particles >= 40, JSON.stringify(l4));
check("boss finisher is the loudest of all", lb.flash && lb.particles >= 52 && lb.kick === 3 && lb.particles > l4.particles, JSON.stringify(lb));

console.log("amp step-up (amp + intense) vs baseline");
const base2 = loudnessSpec({ combo:2, points:100 });
const amp2 = loudnessSpec({ combo:2, points:100, amp:1.4, intense:true });
const base1 = loudnessSpec({ combo:1, points:100 });
const amp1 = loudnessSpec({ combo:1, points:100, amp:1.4, intense:true });
check("amp combo2 throws MORE particles than baseline combo2", amp2.particles > base2.particles, base2.particles+" -> "+amp2.particles);
check("amp flashes at combo 2 (baseline does not)", amp2.flash === true && base2.flash === false);
check("amp combo1 also amplified over baseline", amp1.particles > base1.particles, base1.particles+" -> "+amp1.particles);

console.log("showpiece primitive (×2 reveal / boss finisher)");
{
  const { doc, fx } = build(false);
  const ok = fx.showpiece({spark:["#f00","#fb0"], flash:"rgba(0,0,0,.5)"});
  const parts = doc._fxroot.children.filter(n=>n.className.indexOf("fxparticle")>=0).length;
  const flash = doc._fxroot.children.some(n=>n.className.indexOf("fxflash")>=0);
  const kick = /kick3/.test(doc._wrap.className);
  check("showpiece = flash + full burst + max kick", ok && parts>=52 && flash && kick, "parts="+parts);
  const rm = build(true); const ok2 = rm.fx.showpiece({spark:["#f00"],flash:"rgba(0,0,0,.5)"});
  check("showpiece suppressed under reduce-motion", rm.doc._fxroot.children.length===0);
}

// ---- 4. THE LAW: no coupling to game state / timing ----------------------
console.log("THE LAW: FX cannot touch state, score, combo, records, or timing");
check("no 'state.' references in FX-CORE", !/\bstate\./.test(fxSource));
check("no state.* writes in FX-CORE (combo is read from spec, not global)", !/state\.\w+\s*[+\-]?=/.test(fxSource));
check("no timing (T.questionDone / tStart) in FX-CORE", !/T\.questionDone|tStart|activeMs/.test(fxSource));
check("no setScore / MAX_SCORE in FX-CORE", !/setScore|MAX_SCORE/.test(fxSource));

console.log("");
if (fails) { console.error(fails + " FAILURE(S)"); process.exit(1); }
console.log("fx-core: all green");
