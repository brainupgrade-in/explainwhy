"""Build docs/index.html: a self-contained replay of the recorded runs in samples/outputs/ (served by GitHub Pages).

    python3 scripts/build_replay.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "index.html"


def load_run(d: Path) -> dict:
    result = json.loads((d / "result.json").read_text())
    events = [json.loads(line) for line in (d / "events.jsonl").read_text().splitlines()]
    return {"id": d.name, "result": result, "events": events}


def main() -> None:
    runs = [load_run(d) for d in sorted((ROOT / "samples" / "outputs").iterdir()) if (d / "result.json").is_file()]
    data = json.dumps(runs, default=str).replace("</", "<\\/")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(TEMPLATE.replace("__DATA__", data))
    print(f"wrote {OUT} ({len(runs)} runs, {OUT.stat().st_size // 1024} KB)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ExplainWhy · replay of recorded runs</title>
<style>
  :root { --ink:#1d2433; --muted:#5c6475; --line:#e4e1d8; --bg:#fbfaf7; --accent:#3f6212; --ok:#3f7d1c; --bad:#b4442c; --warn:#a46b00; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:"Inter","Segoe UI","Helvetica Neue",Arial,sans-serif; color:var(--ink); background:var(--bg); }
  header { background:var(--ink); color:#f5f3ee; padding:22px 32px; }
  header h1 { margin:0; font-size:26px; } header p { margin:6px 0 0; color:#b9bfcc; font-size:15px; }
  header a { color:#a3c76d; }
  nav { display:flex; gap:8px; padding:14px 32px; border-bottom:1px solid var(--line); background:#fff; flex-wrap:wrap; }
  nav button { border:1px solid var(--line); background:#fff; border-radius:999px; padding:8px 16px; font-size:14px; cursor:pointer; }
  nav button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
  main { display:grid; grid-template-columns: minmax(340px, 5fr) 7fr; gap:24px; padding:24px 32px; }
  @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
  h2 { font-size:15px; text-transform:uppercase; letter-spacing:1.5px; color:var(--muted); margin:0 0 12px; }
  .q { font-size:22px; font-weight:600; margin:0 0 16px; line-height:1.35; }
  .card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 18px; margin-bottom:14px; }
  .step { display:grid; grid-template-columns: 92px 1fr; gap:10px; padding:9px 0; border-bottom:1px dashed var(--line); font-size:14px; line-height:1.45; }
  .step:last-child { border-bottom:0; }
  .role { font-family:Menlo,Consolas,monospace; font-size:12px; padding:2px 8px; border-radius:6px; align-self:start; text-align:center; }
  .r-planner { background:#efe9fb; color:#5b3fa0; } .r-investigator { background:#e6f3fb; color:#1f6a93; }
  .r-critic { background:#fdeee5; color:#a14d1c; } .r-agent { background:#ecf3e1; color:var(--accent); } .r-user { background:#eee; color:#444; }
  .answer { font-size:18px; line-height:1.55; }
  .claim { padding:10px 0; border-bottom:1px solid var(--line); font-size:15px; line-height:1.5; }
  .claim:last-child { border-bottom:0; }
  .tick { color:var(--ok); font-weight:700; margin-right:6px; } .cross { color:var(--bad); font-weight:700; margin-right:6px; }
  .chip { display:inline-block; font-family:Menlo,Consolas,monospace; font-size:12px; background:#f1f5ea; color:var(--accent);
          border:1px solid #c9d8a8; border-radius:6px; padding:1px 7px; margin:2px 3px 0 0; cursor:pointer; }
  .chip:hover { background:var(--accent); color:#fff; }
  .verdict { font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:1px; }
  .v-supported { color:var(--ok); } .v-refuted, .v-unsupported { color:var(--bad); } .v-partial, .v-open { color:var(--warn); }
  .muted { color:var(--muted); } .small { font-size:13px; }
  .stats { display:flex; gap:18px; flex-wrap:wrap; font-size:13px; color:var(--muted); }
  .stats b { color:var(--ink); }
  dialog { border:0; border-radius:14px; padding:0; width:min(1000px, 94vw); max-height:86vh; }
  dialog::backdrop { background:rgba(20,24,33,.55); }
  .dlg-h { padding:16px 20px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:12px; }
  .dlg-b { padding:16px 20px; overflow:auto; max-height:70vh; }
  pre { background:var(--ink); color:#e8e6df; padding:14px 16px; border-radius:10px; white-space:pre-wrap; font-size:13px; margin:0 0 14px; }
  table { border-collapse:collapse; font-size:13px; width:100%; }
  th, td { border-bottom:1px solid var(--line); padding:5px 8px; text-align:left; font-family:Menlo,Consolas,monospace; }
  th { background:#f6f4ee; position:sticky; top:0; }
  button.x { border:0; background:none; font-size:22px; cursor:pointer; color:var(--muted); }
  footer { padding:10px 32px 30px; color:var(--muted); font-size:13px; }
</style>
</head>
<body>
<header>
  <h1>ExplainWhy · replay of recorded runs</h1>
  <p>Real runs on NVIDIA Nemotron, recorded 27 Oct 2026. Every claim links to the exact SQL and rows behind it.
     Code and demo video: <a href="https://github.com/brainupgrade-in/explainwhy">github.com/brainupgrade-in/explainwhy</a></p>
</header>
<nav id="tabs"></nav>
<main>
  <section>
    <h2>What the agent did</h2>
    <div class="card" id="steps"></div>
  </section>
  <section>
    <h2>Answer</h2>
    <p class="q" id="question"></p>
    <div class="card"><div class="answer" id="summary"></div></div>
    <div class="card"><h2>Verified claims (critic-checked)</h2><div id="claims"></div></div>
    <div class="card" id="dropped-card"><h2>Dropped by the critic</h2><div id="dropped"></div></div>
    <div class="card" id="inf-card"><h2>Inferences (likely causes the data cannot prove)</h2><div id="inferences"></div></div>
    <div class="card"><h2>Hypotheses</h2><div id="hyps"></div></div>
    <div class="card"><div class="stats" id="stats"></div></div>
  </section>
</main>
<footer>Evidence ids (E-xxxxxx) are content hashes of the SQL. Backend for each query is shown in its evidence panel.</footer>
<dialog id="dlg"><div class="dlg-h"><div id="dlg-t"></div><button class="x" onclick="dlg.close()">×</button></div><div class="dlg-b" id="dlg-b"></div></dialog>
<script>
const RUNS = __DATA__;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
let cur = 0;

function evidence(run) { const m = {}; run.events.filter(e => e.type === "evidence_recorded").forEach(e => m[e.entity] = e.payload); return m; }
function chips(ids) { return (ids || []).map(id => `<span class="chip" data-e="${esc(id)}">${esc(id)}</span>`).join(""); }

function render(i) {
  cur = i; const run = RUNS[i], r = run.result, ev = evidence(run);
  document.querySelectorAll("nav button").forEach((b, k) => b.classList.toggle("on", k === i));
  $("question").textContent = r.question;
  $("summary").textContent = r.summary;
  $("claims").innerHTML = r.verified_claims.map(c => `<div class="claim"><span class="tick">✓</span>${esc(c.text)}<br>${chips(c.evidence)}</div>`).join("") || "<p class='muted'>none</p>";
  $("dropped").innerHTML = r.unverified_claims.map(c => `<div class="claim"><span class="cross">✗</span>${esc(c.text)}<br><span class="small muted"><span class="verdict v-${esc(c.verdict)}">${esc(c.verdict)}</span> · ${esc(c.reason)}</span></div>`).join("");
  $("dropped-card").style.display = r.unverified_claims.length ? "" : "none";
  $("inferences").innerHTML = (r.inferences || []).map(x => `<div class="claim">~ ${esc(x.text)}<br><span class="small muted">basis: ${esc(Array.isArray(x.basis) ? x.basis.join(", ") : x.basis)}</span></div>`).join("");
  $("inf-card").style.display = (r.inferences || []).length ? "" : "none";
  $("hyps").innerHTML = Object.entries(r.hypotheses).map(([k, h]) => `<div class="claim"><span class="verdict v-${esc(h.status)}">${esc(h.status)}</span> <span class="small muted">${esc(k)}</span><br>${esc(h.text)}<br>${chips(h.evidence)}${h.why ? `<div class="small muted">${esc(h.why)}</div>` : ""}</div>`).join("");
  const m = r.markovian;
  $("stats").innerHTML = `<span>backend <b>${esc(r.backend)}</b></span><span>model <b>${esc(r.model)}</b></span><span><b>${r.llm_calls}</b> model calls</span><span><b>${r.elapsed_s}</b> s</span><span><b>${r.critic_rounds}</b> critic round(s)</span><span>Markovian: <b>${m.steps}</b> steps, <b>${m.efficiency_percent}%</b> fewer prompt tokens than a full-transcript loop</span>`;
  const rows = [];
  let round = 0;
  run.events.forEach(e => {
    const p = e.payload;
    if (e.type === "question_set") rows.push(["user", "question", esc(p.text)]);
    if (e.type === "hypothesis_proposed") rows.push(["planner", "hypothesis", `<span class="small muted">${esc(e.entity)}</span> ${esc(p.text)}`]);
    if (e.type === "evidence_recorded") rows.push(["investigator", "query", `${chips([e.entity])} ${esc(p.purpose)} <span class="muted">→ ${p.row_count} row(s)</span>`]);
    if (e.type === "hypothesis_updated") rows.push(["investigator", "verdict", `<span class="small muted">${esc(e.entity)}</span> <span class="verdict v-${esc(p.status)}">${esc(p.status)}</span> ${chips(p.evidence)}`]);
    if (e.type === "claim_checked") rows.push(["critic", "check", `<span class="verdict v-${esc(p.verdict)}">${esc(p.verdict)}</span> <span class="small muted">(${esc(p.check)})</span> ${esc(p.text)}<div class="small muted">${esc(p.reason)}</div>`]);
    if (e.type === "answer_set") rows.push(["agent", "answer", `${p.verified} verified, ${p.unverified} dropped`]);
  });
  // collapse consecutive duplicate verdict lines (the investigator restates them at each finish)
  const seen = new Set();
  $("steps").innerHTML = rows.filter(([role, kind, html]) => { if (kind !== "verdict") return true; const k = html; if (seen.has(k)) return false; seen.add(k); return true; })
    .map(([role, kind, html]) => `<div class="step"><span class="role r-${role}">${role}</span><div>${html}</div></div>`).join("");
  document.querySelectorAll(".chip").forEach(c => c.onclick = () => show(c.dataset.e, ev));
}

function show(id, ev) {
  const e = ev[id];
  if (!e) return;
  $("dlg-t").innerHTML = `<b>${esc(id)}</b> · ${esc(e.purpose)}<div class="small muted">backend: ${esc(e.backend)} · ${e.row_count} row(s)</div>`;
  const head = e.columns.map(c => `<th>${esc(c)}</th>`).join("");
  const body = e.rows.slice(0, 200).map(r => `<tr>${r.map(v => `<td>${esc(v)}</td>`).join("")}</tr>`).join("");
  $("dlg-b").innerHTML = `<pre>${esc(e.sql)}</pre><table><thead><tr>${head}</tr></thead><tbody>${body || `<tr><td colspan="${e.columns.length}">(0 rows)</td></tr>`}</tbody></table>`;
  $("dlg").showModal();
}

$("tabs").innerHTML = RUNS.map((run, i) => `<button onclick="render(${i})">${esc(run.id.replace("sample", "Sample "))}: ${esc(run.result.question.slice(0, 60))}…</button>`).join("");
render(0);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
