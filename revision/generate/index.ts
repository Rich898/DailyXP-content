import "jsr:@supabase/functions-js/edge-runtime.d.ts";

// Exam-revision GENERATOR (EXAM-REVISION.md). Given one subject's exam format + a set of
// TOPICS with source grounding, it writes exam-format questions GROUNDED ONLY in that
// grounding (LAW E1), honouring the subject's format (LAW E2) and MC fairness (LAW E3).
// The caller (orchestrator) then runs tools/validate_revision.py before loading.
// Key is the project edge-function secret ANTHROPIC_API_KEY (shared with `coach`).

const MODEL = "claude-opus-5-5";   // generation model — change to dial quality/cost (e.g. claude-sonnet-5-5)

const ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ0a251bWdkbWFseHlqeHZxbHV4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY5Mzc2MTYsImV4cCI6MjEwMjUxMzYxNn0.hynBqLOOsu8Hr7etMlFBhNMUSutZ0Hb8HXL5rpL3rDc";

const CORS: Record<string,string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
function json(obj: unknown, status = 200): Response {
  return new Response(JSON.stringify(obj), { status, headers: { ...CORS, "content-type": "application/json" } });
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ error: "POST only" }, 405);
  const apikey = req.headers.get("apikey") || (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (apikey !== ANON) return json({ error: "unauthorized" }, 401);

  let body: any;
  try { body = await req.json(); } catch { return json({ error: "bad json" }, 400); }
  const subject = String(body.subject || "");
  const year = String(body.year || "Year 9");
  const sections = body.sections || [];
  const allowMc = body.allow_mc !== false;
  const topics = Array.isArray(body.topics) ? body.topics : [];
  const count = Math.min(Math.max(parseInt(body.count) || 8, 1), 20);
  const avoid = Array.isArray(body.avoid) ? body.avoid.slice(0, 40) : [];
  if (!subject || !topics.length) return json({ error: "need subject + topics" }, 400);

  const key = Deno.env.get("ANTHROPIC_API_KEY");
  if (!key) return json({ error: "generator not configured" }, 503);

  const fmt = sections.map((s: any) => `- ${s.name}${s.marks ? " (" + s.marks + " marks)" : ""}: ${s.style || ""}`).join("\n");
  const topicBlock = topics.map((t: any) =>
    `TOPIC ${t.id} — ${t.topic}  [ask as: ${(t.asks_as || []).join("/")}; section: ${t.section || "-"}]\n` +
    `  grounding: ${t.grounding}\n  example style: ${t.exemplar || ""}`).join("\n\n");

  const system = `You write exam-revision questions for a ${year} student revising for their ${subject} yearly exam at an Australian high school. You are given the exam FORMAT and a set of TOPICS, each with source GROUNDING (the facts/model-answer essence from the student's own school materials).

RULES — follow strictly:
- Write exactly ${count} questions, spread across the given topics (favour variety; do not cluster on one topic).
- Ground every question ONLY in the provided grounding for its topic. NEVER invent facts, scenarios, data or sub-topics that are not in the grounding. If the grounding does not support a question, pick another topic.
- Match the exam FORMAT. ${allowMc ? "Multiple choice is allowed for this subject where a topic lists 'mc'." : "This subject has NO multiple choice — never produce an 'mc' question."}
- Use each topic's allowed types (asks_as): "mc", "short" (one or two sentence answer), or "tb" (extended written response).
- Multi-part items (a)/(b) are allowed only where the real exam bundles them; keep them answerable and part-creditable. Prefer one focus otherwise.
- Cover the exam's SECTIONS: if the format has multiple sections, include questions from each; for Science always include at least one Part C — Skills question.
- For "mc": give 4 options and set "a" to the correct index. CRITICAL — length must NOT reveal the answer: write all four options as complete statements of the SAME length (within ~2-3 words of each other). A common mistake is a long fully-worded correct answer with short distractors — never do that; each distractor must be as detailed and plausible as the correct one. Vary which position is correct.
- For "short"/"tb": give a concise, correct "model" answer drawn from the grounding. For "short" you may add "keys": a few distinctive words (omit keys when the answer needs several parts).
- Set "src" to the topic id you used. Set "s" to "${subject}".
- Do NOT repeat or lightly reword any question in the AVOID list.

Reply with STRICT JSON only, no prose, no code fences:
{"questions":[ {"s":"${subject}","t":"short|mc|tb","q":"...","src":"<topic id>", ...type fields... } ]}
mc adds "opts":[...4], "a":<index>, "e":"<why>"; short adds "keys":[...] (optional) and "model":"..."; tb adds "model":"...".`;

  const user = `EXAM FORMAT for ${subject}:\n${fmt}\n\nTOPICS:\n${topicBlock}\n\nAVOID (already asked recently):\n${avoid.join("\n") || "(none)"}\n\nWrite ${count} questions now as strict JSON.`;

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json" },
      body: JSON.stringify({ model: MODEL, max_tokens: 8000, output_config: { effort: "low" }, system, messages: [{ role: "user", content: user }] }),
    });
    if (!r.ok) { const t = await r.text(); return json({ error: "anthropic " + r.status, detail: t.slice(0, 300) }, 502); }
    const data = await r.json();
    const text = (data.content || []).filter((b: any) => b.type === "text").map((b: any) => b.text).join("");
    const a = text.indexOf("{"), b = text.lastIndexOf("}");
    const parsed = JSON.parse(text.slice(a, b + 1));
    const qs = Array.isArray(parsed.questions) ? parsed.questions : [];
    // minimal server-side hygiene; the python validator is the real gate
    const clean = qs.filter((q: any) => q && q.q && q.t && q.src && (!(!allowMc) || q.t !== "mc"));
    return json({ subject, model: MODEL, count: clean.length, questions: clean });
  } catch (e) {
    return json({ error: "generate failed", detail: String(e) }, 500);
  }
});
