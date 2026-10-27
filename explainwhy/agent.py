"""The ExplainWhy loop: recall -> plan hypotheses -> investigate with SQL -> critic -> repair -> answer -> remember.

Roles (all NVIDIA Nemotron):
  planner      turns the question into competing hypotheses
  investigator one bounded Markovian step at a time: run a query, update hypotheses, carry state
  critic       deterministic checks (citations exist, numbers appear in cited rows) + an LLM review;
               unsupported claims send the investigator back for another round (capped)
"""
import json
import re
import time
import uuid
from pathlib import Path

from . import config
from .data import CATALOG, SQLRejected, guard
from .engines.hmem import HMem, tokens
from .engines.markovian import ChunkConfig, MarkovianRun
from .engines.world_model import WorldModel, stable_id
from .llm import LLM

PLANNER_SYS = """You plan investigations over SEC EDGAR data held in Zetaris. Given a "why" question, propose 3-5
competing, testable hypotheses. Include at least one data-artifact explanation (tagging, coverage, duplication,
reference-data gaps) and at least one real-world explanation. Each hypothesis must be checkable with SQL over
the tables below.

TABLES
{catalog}
Reply with JSON only: {{"hypotheses": [{{"text": "...", "how_to_test": "..."}}]}}"""

INVESTIGATOR_SYS = """You are the investigator. You answer a bounded "why" question using ONLY evidence from SQL queries
you run against the tables below. Work one step at a time. Each step, reply with ONE JSON object:

{{"marker": "NEEDS_TOOL" | "TASK_COMPLETE",
  "sql": "one read-only SELECT (NEEDS_TOOL only)", "purpose": "what this query tests", "tests": ["H-..."],
  "hypothesis_updates": [{{"id": "H-...", "status": "supported" | "refuted" | "open", "evidence": ["E-..."]}}],
  "carryover": {{"COMPLETED": "...", "REMAINING": "...", "DECISIONS": "...", "CONTEXT": "..."}},
  "answer": {{"summary": "2-4 sentence direct answer; label anything not shown by the data as likely/inferred",
             "claims": [{{"text": "one factual claim with the exact numbers/dates from the evidence", "evidence": ["E-..."]}}],
             "inferences": [{{"text": "explanation that needs knowledge outside these tables", "basis": "which claims it rests on and why"}}],
             "hypothesis_verdicts": [{{"id": "H-...", "status": "supported" | "refuted", "evidence": ["E-..."], "why": "..."}}]}}
  (answer: TASK_COMPLETE only)}}

Rules:
- SQL dialect: plain ANSI SELECT (Zetaris Lightning SQL / Spark-compatible); qualify tables exactly as listed;
  no semicolons; add LIMIT. Column types are given below: no system catalogs, no casts with ::, no
  database-specific functions. Aggregate (GROUP BY) rather than listing raw rows.
- Never repeat a query; EVIDENCE SO FAR shows each query's first rows.
- Filter companies by cik. A zero-row result only proves absence if the filter values really exist in the table.
- Every claim must cite evidence ids (E-...) whose rows show the claim. Copy numbers exactly from rows.
- Claims are only what the rows show. Causes the data cannot show (accounting standards, business events) go in
  "inferences", stated as likely, never in "claims".
- hypothesis_verdicts must cover every hypothesis id listed under HYPOTHESES.
- Keep replies short: at most 5 claims and 2 inferences, each under 40 words; "why" under 25 words.
- The carryover is REQUIRED every step and is your only memory between steps: fill all four fields, briefly.

TABLES
{catalog}"""

WRITER_SYS = """You write the final answer to a "why" question for a busy analyst. Use ONLY the verified claims given.
You may mention an inference only as likely ("likely because ..."). Add no new facts and no numbers that are not in
the verified claims. 2-4 sentences, plain English, answer the question directly.
Reply with JSON only: {"summary": "..."}"""

CRITIC_SYS = """You are the critic. For each claim, decide if the cited evidence rows (and only those) show it.
"supported" = the rows directly show it; "partial" = mostly, but a number/date/qualifier is not shown;
"unsupported" = the rows do not show it or contradict it. Be strict about numbers and dates.
Reply with JSON only: {"claims": [{"index": 0, "verdict": "supported|partial|unsupported", "reason": "..."}]}"""

NUM = re.compile(r"(?<![\d.])(\d[\d,]*(?:\.\d+)?)")
IDS = re.compile(r"\b[EHCM]-[0-9a-f]{6}\b")


def rows_preview(cols: list[str], rows: list[list], n: int = 25) -> str:
    out = [" | ".join(cols)] + [" | ".join("" if v is None else str(v) for v in r) for r in rows[:n]]
    if len(rows) > n:
        out.append(f"... ({len(rows) - n} more rows, {len(rows)} total)")
    return "\n".join(out) if rows else " | ".join(cols) + "\n(0 rows)"


def is_year(n: str) -> bool:
    return n.isdigit() and 1990 <= int(n) <= 2100


def numbers_in(text: str) -> set[str]:
    """Numbers of 4+ digits (years, dollar values) a claim states; evidence ids are not numbers."""
    return {m.replace(",", "") for m in NUM.findall(IDS.sub("", text)) if len(m.replace(",", "").split(".")[0]) >= 4}


class Investigation:
    def __init__(self, question: str, source, source_note: str, llm: LLM | None = None, run_dir: Path | None = None,
                 log=print):
        self.question, self.source, self.source_note = question.strip(), source, source_note
        self.llm = llm or LLM()
        self.run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]  # unique even within a second
        self.run_dir = run_dir or config.RUNS_DIR / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.world = WorldModel(self.run_dir / "events.jsonl")
        self.memory = HMem(config.MEMORY_DIR)
        self.deadline = time.time() + config.RUN_DEADLINE_S
        self._log_file = (self.run_dir / "trace.log").open("a")
        self._print = log
        self.critic_rounds: list[dict] = []
        self._bounced = False

    def log(self, role: str, msg: str) -> None:
        line = f"{time.strftime('%H:%M:%S')} [{role}] {msg}"
        self._print(line)
        self._log_file.write(line + "\n")
        self._log_file.flush()

    def out_of_time(self) -> bool:
        return time.time() > self.deadline

    # ---------------------------------------------------------------- phases
    def recall(self) -> str:
        hits = self.memory.retrieve(self.question)
        self.recalled = hits
        self.log("memory", f"H-MEM recalled {len(hits)} prior finding(s)" +
                 "".join(f"\n    {h['id']} score={h['score']} {h['content'][:100]}" for h in hits))
        return HMem.reinjection_block(hits)

    def plan(self, memory_block: str) -> None:
        self.world.emit("question_set", "Q", {"text": self.question}, "user")
        plan = self.llm.chat_json([
            {"role": "system", "content": PLANNER_SYS.format(catalog=CATALOG)},
            {"role": "user", "content": f"QUESTION: {self.question}\n\nMEMORY\n{memory_block}"}])
        for h in plan.get("hypotheses", [])[:5]:
            hid = stable_id("H", h["text"])
            self.world.emit("hypothesis_proposed", hid, {"text": h["text"], "how_to_test": h.get("how_to_test", "")}, "planner")
            self.log("planner", f"{hid}: {h['text']}")

    def run_sql(self, sql: str, purpose: str, tests: list[str]) -> str:
        try:
            safe = guard(sql)
        except SQLRejected as e:
            self.log("guard", f"rejected: {e}")
            return f"QUERY REJECTED by read-only guard: {e}. Write one SELECT."
        eid = stable_id("E", safe)
        if eid in self.world.state()["evidence"]:
            self.log("sql", f"{eid} repeated query refused")
            return f"You already ran this exact query as {eid}; its rows are above in EVIDENCE SO FAR. Ask something new or finish."
        self.log("sql", f"{eid} {purpose}\n    {' '.join(safe.split())[:300]}")
        try:
            cols, rows = self.source.query(safe)
        except Exception as e:
            self.log("sql", f"{eid} error: {str(e)[:200]}")
            return f"QUERY ERROR for {eid}: {str(e)[:400]}. Fix the SQL (check table/column names) and retry."
        rows = rows[:200]
        self.world.emit("evidence_recorded", eid, {"sql": safe, "purpose": purpose, "tests": tests, "columns": cols,
                                                    "rows": rows, "row_count": len(rows), "backend": self.source.name},
                        "investigator")
        self.log("sql", f"{eid} -> {len(rows)} row(s)")
        return f"{eid} ({purpose}):\n{rows_preview(cols, rows)}"

    def investigate(self, mk: MarkovianRun, observation: str, max_steps: int) -> dict | None:
        for i in range(max_steps + 1):  # the extra pass is a forced-finish step
            last = i >= max_steps - 1
            if self.out_of_time():
                self.log("investigator", "deadline reached")
                mk.status = "deadline"
                return None
            st = self.world.state()
            hyp = "\n".join(f"- {k} [{v['status']}] {v['text']} (evidence: {', '.join(v['evidence']) or '-'})"
                            for k, v in st["hypotheses"].items())
            ev = "\n".join(f"- {k}: {v['purpose']} ({v['row_count']} rows)\n  " +
                           rows_preview(v["columns"], v["rows"], 6).replace("\n", "\n  ") for k, v in st["evidence"].items()) or "-"
            context = mk.prompt_context(observation)
            budget = ("LAST STEP: reply with marker TASK_COMPLETE now, using only the evidence you have."
                      if last else f"Steps left in this round: {max_steps - i}. Finish as soon as every hypothesis has a verdict.")
            prompt = f"QUESTION: {self.question}\n\n{context}\n\nHYPOTHESES\n{hyp}\n\nEVIDENCE SO FAR\n{ev}\n\n{budget}"
            try:
                step = self.llm.chat_json([{"role": "system", "content": INVESTIGATOR_SYS.format(catalog=CATALOG)},
                                           {"role": "user", "content": prompt}], max_tokens=4096)
            except ValueError as e:  # unparseable even after the repair turn: tell the model, do not crash
                self.log("investigator", f"unparseable reply ({e}); retrying with a shorter-answer instruction")
                observation = "Your last reply was not valid JSON (likely too long). Reply with a SHORTER JSON object."
                mk.record("STATE_CHECKPOINT", prompt, "", None, observation)
                continue
            marker = step.get("marker", "NEEDS_TOOL")
            updates = (step.get("hypothesis_updates") or []) + ((step.get("answer") or {}).get("hypothesis_verdicts") or [])
            for u in updates:
                if u.get("id") in st["hypotheses"] and u.get("status") in ("supported", "refuted", "open"):
                    valid = [e for e in u.get("evidence", []) if e in st["evidence"]]
                    self.world.emit("hypothesis_updated", u["id"], {"status": u["status"], "evidence": valid,
                                                                    "why": u.get("why", "")}, "investigator")
                    self.log("investigator", f"{u['id']} -> {u['status']} {valid}")
            if marker == "TASK_COMPLETE":
                if not st["evidence"]:
                    observation = "You cannot finish without evidence. Run a query first."
                    mk.record("STATE_CHECKPOINT", prompt, json.dumps(step), step.get("carryover"), observation)
                    continue
                still_open = [k for k, v in self.world.state()["hypotheses"].items() if v["status"] == "open"]
                if still_open and not self._bounced and not last:
                    self._bounced = True
                    observation = (f"Not finished: hypotheses {', '.join(still_open)} have no verdict. Give each a "
                                   "supported/refuted verdict with evidence (run a query if needed), then finish.")
                    mk.record("STATE_CHECKPOINT", prompt, json.dumps(step), step.get("carryover"), observation)
                    continue
                mk.record("TASK_COMPLETE", prompt, json.dumps(step), step.get("carryover"), "")
                self.log("investigator", "[TASK_COMPLETE]")
                return step.get("answer") or {}
            if i >= max_steps:
                break
            observation = self.run_sql(step.get("sql", ""), step.get("purpose", ""), step.get("tests", []))
            mk.record("NEEDS_TOOL", prompt, json.dumps(step), step.get("carryover"), observation)
            self.log("markovian", f"step {len(mk.chunks)} [STATE_CHECKPOINT] carryover: "
                                  f"{str(mk.carryover.get('REMAINING', ''))[:160]}")
        mk.status = "max-chunks"
        return None

    def vacuous_filters(self, ev: dict) -> list[str]:
        """For an empty/zero result: filter literals (col = 'x') that match nothing in the table, so the zero proves nothing."""
        rows = ev["rows"]
        empty = not rows or (len(rows) == 1 and all(v in (0, "0", None) for v in rows[0]))
        table = re.search(r"(?i)\bfrom\s+([\w.]+)", ev["sql"])
        where = re.search(r"(?is)\bwhere\b(.*)", ev["sql"])
        # A one-condition probe ("no row has sic_code = '3570'") is itself the evidence; only a zero from a
        # multi-condition filter can hide a mistyped value (entity_name = 'Apple' AND fiscal_year > 2018).
        if not empty or not table or not where or not re.search(r"(?i)\band\b", where.group(1)):
            return []
        bad = []
        for col, lit in re.findall(r"(?i)\b(\w+)\s*=\s*'([^']*)'", ev["sql"]):
            try:
                probe = guard(f"SELECT COUNT(*) FROM {table.group(1)} WHERE {col} = '{lit}'")
                _, r = self.source.query(probe)
            except Exception:
                continue
            if r and r[0][0] in (0, "0"):
                bad.append(f"{col} = '{lit}'")
        return bad

    def critique(self, answer: dict) -> list[dict]:
        st = self.world.state()
        claims = answer.get("claims") or []
        results = []
        for i, c in enumerate(claims):
            cited = [e for e in c.get("evidence", []) if e in st["evidence"]]
            if not cited:
                results.append({"index": i, "verdict": "unsupported", "reason": "cites no recorded evidence", "check": "deterministic"})
                continue
            # A number may come from the rows or from the query itself (e.g. "after 2018" <- WHERE fiscal_year > 2018).
            text = " ".join(st["evidence"][e]["sql"] + " " + rows_preview(st["evidence"][e]["columns"], st["evidence"][e]["rows"], 200)
                            for e in cited)
            haystack = set(re.findall(r"\d+(?:\.\d+)?", text.replace(",", "")))  # whole numbers, not substrings
            missing = [n for n in numbers_in(c["text"]) if n not in haystack and n.split(".")[0] not in haystack
                       and not (is_year(n) and {str(int(n) - 1), str(int(n) + 1)} & haystack)]  # "after 2018" ~ ">= 2019"
            vacuous = {e: v for e in cited if (v := self.vacuous_filters(st["evidence"][e]))}
            if missing:
                results.append({"index": i, "verdict": "unsupported", "check": "deterministic",
                                "reason": f"number(s) {', '.join(missing)} not found in cited evidence {cited}"})
            elif vacuous and len(vacuous) == len(cited):
                results.append({"index": i, "verdict": "unsupported", "check": "deterministic",
                                "reason": "zero result proves nothing: filter(s) " + "; ".join(
                                    f"{e}: {', '.join(v)}" for e, v in vacuous.items()) + " match no rows in the table"})
            else:
                results.append(None)
        pending = [i for i, r in enumerate(results) if r is None]
        if pending:
            blocks = []
            for i in pending:
                c = claims[i]
                ev = "\n".join(f"{e} SQL: {st['evidence'][e]['sql']}\n{rows_preview(st['evidence'][e]['columns'], st['evidence'][e]['rows'], 40)}"
                               for e in c["evidence"] if e in st["evidence"])
                blocks.append(f"CLAIM {i}: {c['text']}\nCITED EVIDENCE:\n{ev}")
            review = self.llm.chat_json([{"role": "system", "content": CRITIC_SYS},
                                         {"role": "user", "content": "\n\n".join(blocks)}])
            got = review.get("claims", [])
            by_index = {r.get("index"): r for r in got}
            if not all(i in by_index for i in pending) and len(got) == len(pending):
                by_index = dict(zip(pending, got))  # critic numbered its replies 0..n-1 instead of by claim index
            for i in pending:
                r = by_index.get(i, {"verdict": "unsupported", "reason": "critic gave no verdict"})
                results[i] = {"index": i, "verdict": r.get("verdict", "unsupported"), "reason": r.get("reason", ""), "check": "llm"}
        for r in results:
            cid = stable_id("C", claims[r["index"]]["text"])
            self.world.emit("claim_checked", cid, {**r, "text": claims[r["index"]]["text"],
                                                   "evidence": claims[r["index"]].get("evidence", [])}, "critic",
                            idem=f"claim:{cid}:{len(self.critic_rounds)}")
            self.log("critic", f"claim {r['index']} {r['verdict'].upper()} ({r['check']}): {r['reason'][:150]}")
        self.critic_rounds.append({"round": len(self.critic_rounds) + 1, "results": results})
        return results

    def remember(self, answer: dict, verdicts: list[dict]) -> int:
        st, n = self.world.state(), 0
        for r in verdicts:
            if r["verdict"] not in ("supported", "partial"):
                continue
            c = answer["claims"][r["index"]]
            sqls = [st["evidence"][e]["sql"] for e in c["evidence"] if e in st["evidence"]]
            ents = sorted({w for w in ("apple", "ibm", "tesla", "revenues", "sic", "asc", "606") if w in c["text"].lower()})
            self.memory.write(c["text"], source="zetaris:" + ";".join(c["evidence"]), entities=ents, tags=["edgar"] + ents,
                              confidence=0.85 if r["verdict"] == "supported" else 0.6,
                              provenance_label=f"verified by critic in run {self.run_id}", refs=sqls,
                              actor="critic", mission_id=self.run_id)
            n += 1
        claim_tokens = set().union(*(tokens(answer["claims"][r["index"]]["text"]) for r in verdicts
                                     if r["verdict"] == "supported")) if verdicts else set()
        for h in self.recalled:
            m = tokens(h["content"])
            if m and len(m & claim_tokens) / len(m) >= 0.5:
                self.memory.feedback(h["id"], "helpful", "critic")
        return n

    # ------------------------------------------------------------------ main
    def run(self) -> dict:
        t0 = time.time()
        self.log("harness", f"backend: {self.source_note}; model: {self.llm.model}" + (" (replay)" if self.llm.replay else ""))
        self.plan(self.recall())
        mk = MarkovianRun(ChunkConfig(max_chunks=min(32, config.MAX_STEPS * (config.MAX_REPAIR_ROUNDS + 1))), self.question)
        answer, verdicts, observation = None, [], ""
        for round_ in range(config.MAX_REPAIR_ROUNDS + 1):
            answer = self.investigate(mk, observation, config.MAX_STEPS) or answer
            if not answer:
                break
            verdicts = self.critique(answer)
            bad = [r for r in verdicts if r["verdict"] != "supported"]
            if not bad or round_ == config.MAX_REPAIR_ROUNDS or self.out_of_time():
                break
            observation = "CRITIC FEEDBACK -- fix these claims with more evidence, correct them, or drop them:\n" + \
                "\n".join(f"- claim {r['index']} ({answer['claims'][r['index']]['text'][:160]}): {r['verdict']} -- {r['reason']}"
                          for r in bad)
            self.log("critic", f"{len(bad)} claim(s) not supported -> repair round {round_ + 1}")
        if mk.status == "running":
            mk.status = "completed" if answer else "errored"
        stored = self.remember(answer, verdicts) if answer else 0
        if answer:
            answer["summary"] = self.write_summary(answer, verdicts)
        result = self.finish(answer, verdicts, mk, stored, time.time() - t0)
        self._log_file.close()
        return result

    def write_summary(self, answer: dict, verdicts: list[dict]) -> str:
        """Final answer composed from critic-verified claims only; numbers checked against those claims."""
        ok = [answer["claims"][r["index"]]["text"] for r in verdicts if r["verdict"] == "supported"]
        if not ok:
            return "No claim survived the critic, so there is no evidence-backed answer. See the dropped claims below."
        inferences = [x.get("text", "") for x in answer.get("inferences") or []]
        try:
            summary = self.llm.chat_json([{"role": "system", "content": WRITER_SYS},
                                          {"role": "user", "content": f"QUESTION: {self.question}\n\nVERIFIED CLAIMS\n" +
                                           "\n".join(f"- {c}" for c in ok) + "\n\nINFERENCES (not proven)\n" +
                                           ("\n".join(f"- {x}" for x in inferences) or "-")}]).get("summary", "")
        except ValueError:
            summary = ""
        allowed = set().union(*(numbers_in(c) for c in ok))
        extra = [n for n in numbers_in(summary) if n not in allowed and not (is_year(n) and {str(int(n) - 1), str(int(n) + 1)} & allowed)]
        if not summary or extra:
            self.log("writer", f"summary rejected ({'new numbers ' + ', '.join(extra) if extra else 'empty'}); using verified claims")
            return " ".join(ok)
        self.log("writer", "summary written from verified claims")
        return summary

    def finish(self, answer, verdicts, mk, stored, elapsed) -> dict:
        st = self.world.state()
        ok = [answer["claims"][r["index"]] | {"verdict": r["verdict"]} for r in verdicts if r["verdict"] == "supported"] if answer else []
        dropped = [answer["claims"][r["index"]] | {"verdict": r["verdict"], "reason": r["reason"]}
                   for r in verdicts if r["verdict"] != "supported"] if answer else []
        result = {"question": self.question, "run_id": self.run_id, "backend": self.source.name, "model": self.llm.model,
                  "summary": (answer or {}).get("summary", "No answer within the step/time budget."),
                  "verified_claims": ok, "unverified_claims": dropped, "inferences": (answer or {}).get("inferences", []),
                  "hypotheses": st["hypotheses"], "evidence": {k: {kk: v[kk] for kk in ("sql", "purpose", "row_count")}
                                                               for k, v in st["evidence"].items()},
                  "critic_rounds": len(self.critic_rounds), "memories_written": stored,
                  "markovian": mk.stats(), "llm_calls": self.llm.calls, "elapsed_s": round(elapsed, 1)}
        self.world.emit("answer_set", "A", {"summary": result["summary"], "verified": len(ok), "unverified": len(dropped)}, "agent")
        (self.run_dir / "result.json").write_text(json.dumps(result, indent=2, default=str))
        (self.run_dir / "report.md").write_text(render_report(result, st))
        self.log("agent", f"done in {result['elapsed_s']}s: {len(ok)} verified claim(s), {len(dropped)} unverified; "
                          f"report {self.run_dir / 'report.md'}")
        return result


def render_report(r: dict, st: dict) -> str:
    out = [f"# {r['question']}", "", f"**Answer.** {r['summary']}", "",
           "## Verified claims (critic-checked against query results)"]
    out += [f"- {c['text']} — evidence: {', '.join(c['evidence'])}" for c in r["verified_claims"]] or ["- none"]
    if r["unverified_claims"]:
        out += ["", "## Claims the critic did not accept (not part of the answer)"]
        out += [f"- {c['text']} — {c['verdict']}: {c['reason']}" for c in r["unverified_claims"]]
    if r["inferences"]:
        out += ["", "## Inferences (likely causes the data cannot prove; not critic-verified)"]
        out += [f"- {x.get('text')} — basis: {x.get('basis', '')}" for x in r["inferences"]]
    out += ["", "## Hypotheses"] + [f"- `{k}` **{v['status']}** — {v['text']} ({', '.join(v['evidence']) or 'no evidence'})"
                                    + (f"<br>why: {v['why']}" if v.get("why") else "") for k, v in st["hypotheses"].items()]
    out += ["", "## Evidence (Zetaris SQL)"]
    for k, v in st["evidence"].items():
        out += [f"### {k} — {v['purpose']}", f"Backend: {v['backend']}, {v['row_count']} row(s)", "```sql", v["sql"], "```",
                "```", rows_preview(v["columns"], v["rows"], 12), "```"]
    m = r["markovian"]
    out += ["", "## Run", f"- backend `{r['backend']}`, model `{r['model']}`, {r['llm_calls']} LLM calls, {r['elapsed_s']} s",
            f"- Markovian: {m['steps']} steps, {m['prompt_tokens_used']} prompt tokens vs ~{m['full_transcript_estimate']} "
            f"for a full-transcript loop ({m['efficiency_percent']}% saved)",
            f"- critic rounds: {r['critic_rounds']}; H-MEM memories written: {r['memories_written']}"]
    return "\n".join(out) + "\n"
