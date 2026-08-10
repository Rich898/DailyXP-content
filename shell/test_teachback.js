// XPDaily — teach-back effort-gate proof.
// The client gate is the EFFORT layer: it must ACCEPT any genuine English attempt (of any
// quality) and REJECT obvious non-attempts (mashing, single-word/char repetition, non-English).
// It is deliberately PERMISSIVE — real quality/correctness/language grading is the server LLM's
// job. This test locks the two properties: no false-negatives on real answers, and the crude
// garbage classes are caught.
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");
const m = src.match(/var TB_COMMON =[\s\S]*?function teachbackReady\(v\)\{[\s\S]*?\n\}/);
if (!m) { console.error("FAIL: teachbackReady not found"); process.exit(1); }
const ready = new Function(m[0] + "; return teachbackReady;")();

let fails = 0;
const accept = (v, why) => { const r = ready(v); console.log((r.ok ? "  ok   " : "  FAIL ") + "ACCEPT " + why); if (!r.ok) fails++; };
const reject = (v, why) => { const r = ready(v); console.log((!r.ok ? "  ok   " : "  FAIL ") + "REJECT " + why); if (r.ok) fails++; };

console.log("real English attempts must ACCEPT (no false-negatives):");
accept("Cells respire to release energy from glucose, and this happens in all living things, not just plants, because every cell needs energy to do its work.", "full explanation");
accept("respiration is when a cell makes energy, it needs oxygen and gives out carbon dioxide, and all living things do it not just plants", "ESL-phrased but real");
accept("A metaphor says one thing is another to paint a picture, like calling the classroom a zoo, and it has no like or as, which is what makes it different from a simile.", "lit answer");
accept("You undo the plus six first by taking six off both sides, then divide by two, so you get x on its own in two clean steps.", "maths method in words");

console.log("obvious non-attempts must REJECT:");
reject("a".repeat(90), "single char repeated");
reject(Array(20).fill("asdf").join(" "), "keyboard mash repeated");
reject(Array(22).fill("the").join(" "), "one word repeated");
reject("La respiration cellulaire libere de l'energie a partir du glucose dans toutes les cellules vivantes des animaux et plantes", "non-English (French)");
reject("qwerty uiop zxcvb nmlkj hgfds poiuy trewq lkjhg fdsaz mnbvc xzasd qwert plmko", "non-word tokens");
reject("short answer here", "too short");
reject("", "empty");

console.log("");
if (fails) { console.error(fails + " FAILURE(S)"); process.exit(1); }
console.log("teachback effort-gate: all green");
