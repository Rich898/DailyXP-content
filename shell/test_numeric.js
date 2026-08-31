// XPDaily — Numeric input proof (decimal + fraction upgrade, 31 Aug 2026).
// Live-fire bugs this locks against (both hit t1 on T6.1, 31 Aug):
//   * a MENTAL slot with answer 0.4 was unanswerable — the number pad had no '.' key;
//   * an "as a fraction" slot had no way to write a fraction on either pad.
// Sources extracted VERBATIM from shell/template_v3.html between the NUMERIC-WIDGET
// and NUMERIC-CORE markers, driven with a stub DOM (house pattern, same as test_scrub.js).
// The contract:
//   1. Mental pad carries '.' and the a/b fraction key; calc pad carries '/' too.
//   2. Decimal answers are typeable and judged on BOTH pads.
//   3. A fraction a/b earns credit by VALUE: 0.4 == 2/5 == 4/10; 3/8 does not.
//   4. Writing a fraction NEVER counts as calculator use (usedCalc stays honest);
//      computing with ÷/= still does.
//   5. The fraction bar binds tighter than ÷ (8÷4/2 = 8÷(4/2) = 4).
//   6. Mental pad: ONE fraction per answer; '.' once per number segment; ± still works.
//   7. Reveal honours an authored `frac` display form ("2/5 (= 0.4)").
//   8. numericOK (the shared typed matcher) accepts equivalent fractions too.
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
const widgetSrc = grab("/*NUMERIC-WIDGET-START*/", "/*NUMERIC-WIDGET-END*/");
const coreSrc = grab("/*NUMERIC-CORE-START*/", "/*NUMERIC-CORE-END*/");

// ---------------- source-level contract ------------------------------------
console.log("SOURCE CONTRACT");
check("mental pad has '.' and '/' (the live-fire fix)", /NUM_KEYS =\[\['7','8','9'\],\['4','5','6'\],\['1','2','3'\],\['\.','0','\/'\],\['\\u00b1','\\u232b'\]\]/.test(widgetSrc));
check("calc pad has '/' beside '.'", /\['0','\.','\/','\+'\],\['='\]/.test(widgetSrc));
check("fraction bar binds tighter than \u00f7", /prec=\{'\+':1,'-':1,'\*':2,':':2,'\/':3\}/.test(widgetSrc));
check("one evaluator for both pads", widgetSrc.indexOf("var val = evalExpr(entry);") >= 0);

// ---------------- stub DOM -------------------------------------------------
function makeNode(tag) {
  const node = {
    tagName: tag, className: "", _attrs: {}, children: [], style: {}, _html: "",
    _listeners: {}, disabled: false, readOnly: false,
    setAttribute(k, v) { node._attrs[k] = v; },
    getAttribute(k) { return node._attrs[k]; },
    addEventListener(ev, fn) { (node._listeners[ev] = node._listeners[ev] || []).push(fn); },
    dispatch(ev, e) { (node._listeners[ev] || []).forEach(fn => fn(e || {})); },
    classList: {
      add(...c) { const s = new Set(node.className.split(/\s+/).filter(Boolean)); c.forEach(x => s.add(x)); node.className = [...s].join(" "); },
      remove(...c) { const s = new Set(node.className.split(/\s+/).filter(Boolean)); c.forEach(x => s.delete(x)); node.className = [...s].join(" "); },
      contains(c) { return node.className.split(/\s+/).indexOf(c) >= 0; },
    },
    get offsetWidth() { return 360; },
    querySelector(sel) { return node._find(sel)[0] || null; },
    querySelectorAll(sel) { return node._find(sel); },
    _find(sel) {
      const out = [];
      const id = sel.charAt(0) === "#" ? sel.slice(1) : null;
      const cls = sel.charAt(0) === "." ? sel.slice(1) : null;
      const walk = (n) => {
        n.children.forEach(ch => {
          if ((id && ch._attrs.id === id) || (cls && ch.className.split(/\s+/).indexOf(cls) >= 0)) out.push(ch);
          walk(ch);
        });
      };
      walk(node);
      return out;
    },
    set innerHTML(html) {
      node._html = html; node.children = [];
      // minimal parse: one child per top-level tag carrying class/id/data-k
      const re = /<(div|button)\s+([^>]*)>/g; let m;
      while ((m = re.exec(html))) {
        const ch = makeNode(m[1]); const attrs = m[2];
        const idm = attrs.match(/id="([^"]*)"/); if (idm) ch._attrs.id = idm[1];
        const cm = attrs.match(/class="([^"]*)"/); if (cm) ch.className = cm[1];
        const km = attrs.match(/data-k="([^"]*)"/); if (km) ch._attrs["data-k"] = km[1];
        node.children.push(ch);
      }
    },
    get innerHTML() { return node._html; },
  };
  return node;
}
function build() {
  const headKids = [];
  const doc = {
    createElement: (t) => makeNode(t),
    getElementById: (id) => headKids.find(n => n._attrs.id === id) || null,
    head: { appendChild(n) { headKids.push(n); return n; } },
  };
  const timeouts = [];
  const fakeTimeout = (fn, ms) => { timeouts.push(ms); fn(); };
  const f = new Function("window", "document", "navigator", "setTimeout",
    widgetSrc + "\n;return {mountNumeric:mountNumeric};");
  return { api: f({}, doc, {}, fakeTimeout), timeouts };
}
function mountQ(q, cb) {
  const b = build();
  const container = makeNode("div");
  b.api.mountNumeric(container, q, cb);
  const keys = container.querySelector(".nm-keys");
  return {
    container, timeouts: b.timeouts,
    press(k) {
      const btn = keys._find(".nm-key").find(x => x.getAttribute("data-k") === k);
      if (!btn) throw new Error("no key: " + k);
      btn.dispatch("click");
    },
    keycaps() { return keys._find(".nm-key").map(x => x.getAttribute("data-k")); },
    display() { return container.querySelector("#nmDisp").innerHTML; },
    submit() { container.querySelector("#nmSubmit").dispatch("click"); },
    result() { return container.querySelector("#nmResult").innerHTML; },
  };
}
const MENTAL = () => ({ prompt: "P(not green)?", answer: 0.4, calc: false, pre: "", post: "", why: "1 − 0.6 = 0.4." });
const CALC = () => ({ prompt: "P(yellow) from 4 of 10?", answer: 0.4, calc: true, pre: "", post: "", why: "4 out of 10." });

(async function run() {
  console.log("PAD BEHAVIOUR");
  { // N1 — THE live-fire bug: mental decimal
    let res = null; const m = mountQ(MENTAL(), (r) => { res = r; });
    check("N1 mental pad exposes . / \u00b1 \u232b", ["."].concat(["/", "\u00b1", "\u232b"]).every(k => m.keycaps().indexOf(k) >= 0), m.keycaps().join(","));
    check("N1 fraction key wears the a/b label", m.container.querySelector(".nm-keys")._html.indexOf(">a/b</button>") >= 0);
    m.press("0"); m.press("."); m.press("4"); m.submit();
    check("N1 mental 0.4 accepted (was UNANSWERABLE)", res && res.ok === true && res.value === 0.4, JSON.stringify(res));
    check("N1 mental never counts as calculator", res && res.usedCalc === false);
  }
  { // N2 — mental fraction, equivalent forms
    let res = null; let m = mountQ(MENTAL(), (r) => { res = r; });
    m.press("2"); m.press("/"); m.press("5"); m.submit();
    check("N2 mental 2/5 == 0.4 earns credit", res && res.ok === true, JSON.stringify(res));
    res = null; m = mountQ(MENTAL(), (r) => { res = r; });
    m.press("4"); m.press("/"); m.press("1"); m.press("0"); m.submit();
    check("N2 mental 4/10 == 0.4 earns credit", res && res.ok === true);
    check("N2 writing a fraction is not calculator use", res && res.usedCalc === false);
    res = null; m = mountQ(MENTAL(), (r) => { res = r; });
    m.press("3"); m.press("/"); m.press("8"); m.submit();
    check("N2 mental 3/8 is wrong (0.375 \u2260 0.4)", res && res.ok === false);
  }
  { // N3 — mental guard rails
    let res = null; let m = mountQ(MENTAL(), (r) => { res = r; });
    m.press("/"); m.press("5"); m.submit();          // leading '/' refused \u2192 entry is just "5"
    check("N3 '/' with no number in front is refused", res && res.value === 5, JSON.stringify(res));
    res = null; m = mountQ(MENTAL(), (r) => { res = r; });
    m.press("1"); m.press("/"); m.press("2"); m.press("/");   // one fraction per answer
    m.submit();
    check("N3 second '/' refused \u2192 1/2 submits as 0.5", res && res.ok === false && res.value === 0.5, JSON.stringify(res));
  }
  { // N4 — mental: '.' once per segment, on both sides of the bar
    let res = null; const m = mountQ({ prompt: "", answer: 0.5, calc: false, pre: "", post: "", why: "" }, (r) => { res = r; });
    m.press("1"); m.press("."); m.press("5"); m.press(".");   // second '.' in the segment refused
    m.press("/"); m.press("3"); m.submit();
    check("N4 1.5/3 = 0.5 accepted; duplicate '.' refused", res && res.ok === true && res.value === 0.5, JSON.stringify(res));
  }
  { // N5 — mental negative fraction via ±
    let res = null; const m = mountQ({ prompt: "", answer: -0.4, calc: false, pre: "", post: "", why: "" }, (r) => { res = r; });
    m.press("4"); m.press("/"); m.press("1"); m.press("0"); m.press("\u00b1"); m.submit();
    check("N5 \u00b1 4/10 \u2192 -0.4 accepted", res && res.ok === true && res.value === -0.4, JSON.stringify(res));
  }
  console.log("CALC BEHAVIOUR");
  { // N6 — calculator still computes; usedCalc honest both ways
    let res = null; let m = mountQ(CALC(), (r) => { res = r; });
    m.press("4"); m.press("\u00f7"); m.press("1"); m.press("0"); m.press("="); m.submit();
    check("N6 4\u00f710= \u2192 0.4, usedCalc:true", res && res.ok === true && res.usedCalc === true, JSON.stringify(res));
    res = null; m = mountQ(CALC(), (r) => { res = r; });
    m.press("2"); m.press("/"); m.press("5"); m.submit();
    check("N6 2/5 typed as the ANSWER \u2192 ok, usedCalc:false", res && res.ok === true && res.usedCalc === false, JSON.stringify(res));
  }
  { // N7 — precedence: the fraction bar binds tighter than ÷
    let res = null; const m = mountQ({ prompt: "", answer: 4, calc: true, pre: "", post: "", why: "" }, (r) => { res = r; });
    m.press("8"); m.press("\u00f7"); m.press("4"); m.press("/"); m.press("2"); m.submit();
    check("N7 8\u00f74/2 = 8\u00f7(4/2) = 4", res && res.ok === true && res.value === 4, JSON.stringify(res));
  }
  { // N8 — reveal honours the authored fraction form
    let res = null; const q = MENTAL(); q.frac = "2/5";
    const m = mountQ(q, (r) => { res = r; });
    m.press("7"); m.submit();
    check("N8 wrong \u2192 strip shows '2/5 (= 0.4)'", m.result().indexOf("2/5 (= 0.4)") >= 0, m.result().slice(0, 90));
  }
  // ---------------- numericOK (the shared typed matcher) --------------------
  console.log("NUMERIC-CORE (numericOK)");
  const core = new Function(coreSrc + "\n;return {numericOK:numericOK};")();
  check("C1 bare decimal still matches", core.numericOK("0.4", { answer: 0.4 }) === true);
  check("C2 fraction matches by value", core.numericOK("4/10", { answer: 0.4 }) === true && core.numericOK("2/5", { answer: 0.4 }) === true);
  check("C3 wrong fraction rejected", core.numericOK("3/8", { answer: 0.4 }) === false);
  check("C4 1/3 within tolerance of 0.33", core.numericOK("1/3", { answer: 0.33 }) === true);
  check("C5 unit forms still accepted", core.numericOK("105 cm2", { answer: 105, accept: ["105 cm\u00b2"] }) === true);
  check("C6 empty / null still rejected", core.numericOK("", { answer: 1 }) === false && core.numericOK(null, { answer: 1 }) === false);

  console.log(fails ? "\nRESULT: " + fails + " FAILING" : "\nRESULT: all pass");
  process.exit(fails ? 1 : 0);
})();
