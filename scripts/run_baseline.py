"""Baselines for the eval set, scored exactly like the agent (evals/questions.json patterns).

  B1  Nemotron alone: the table catalog, no data access, one call.
  B2  One-shot text-to-SQL: Nemotron writes one query, we run it, Nemotron answers from the rows.
      No hypotheses, no critic, no repair.

Also counts claims stating a 4+-digit number (year, value, code) that no query result backs up.
Same local data mirror and model as the agent eval.

    python3 scripts/run_baseline.py   # writes evals/baseline.md and evals/baseline_runs.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from explainwhy import config  # noqa: E402
from explainwhy.agent import is_year, numbers_in  # noqa: E402
from explainwhy.data import CATALOG, LocalSource, guard  # noqa: E402
from explainwhy.llm import LLM  # noqa: E402

ANSWER_SPEC = ('Reply with JSON only: {"summary": "2-4 sentences", "claims": ["one factual claim per item, with exact '
               'numbers and dates"]}')


def unbacked(claims: list[str], evidence_text: str) -> int:
    nums = set(re.findall(r"\d+(?:\.\d+)?", evidence_text.replace(",", "")))
    bad = 0
    for c in claims:
        missing = [n for n in numbers_in(c) if n not in nums
                   and not (is_year(n) and {str(int(n) - 1), str(int(n) + 1)} & nums)]
        bad += bool(missing)
    return bad


def passes(claims: list[str], expect: list[str]) -> tuple[bool, list[str]]:
    missing = [p for p in expect if not any(re.search(p, c, re.I) for c in claims)]
    return bool(claims) and not missing, missing


def main() -> None:
    config.LLM_CACHE_DIR = ROOT / "evals" / "llm_cache_baseline"
    llm, source = LLM(), LocalSource()
    questions = json.loads((ROOT / "evals" / "questions.json").read_text())
    runs, rows, score = [], [], {"B1": 0, "B2": 0}
    for q in questions:
        # B1: no data
        b1 = llm.chat_json([{"role": "system", "content": "You are a financial data analyst. Answer the question using "
                             "your own knowledge and this schema. You cannot run queries.\n\nTABLES\n" + CATALOG + "\n" + ANSWER_SPEC},
                            {"role": "user", "content": q["question"]}])
        b1_claims = [str(c) for c in b1.get("claims", [])]
        b1_ok, b1_miss = passes(b1_claims, q["expect"])
        # B2: one query, then answer
        plan = llm.chat_json([{"role": "system", "content": "Write ONE read-only SQL SELECT (plain ANSI, tables exactly as "
                               "listed, filter companies by cik) whose result best answers the question.\n\nTABLES\n" + CATALOG +
                               '\nReply with JSON only: {"sql": "..."}'},
                              {"role": "user", "content": q["question"]}])
        try:
            sql = guard(plan.get("sql", ""))
            cols, data = source.query(sql)
            result = " | ".join(cols) + "\n" + "\n".join(" | ".join(map(str, r)) for r in data[:60])
        except Exception as e:  # a bad query is part of the baseline's result, not a crash
            sql, result = plan.get("sql", ""), f"QUERY FAILED: {e}"
        b2 = llm.chat_json([{"role": "system", "content": "Answer the question using ONLY this query result.\n" + ANSWER_SPEC},
                            {"role": "user", "content": f"QUESTION: {q['question']}\n\nSQL: {sql}\n\nRESULT:\n{result}"}])
        b2_claims = [str(c) for c in b2.get("claims", [])]
        b2_ok, b2_miss = passes(b2_claims, q["expect"])
        score["B1"] += b1_ok
        score["B2"] += b2_ok
        n1, n2 = unbacked(b1_claims, ""), unbacked(b2_claims, sql + " " + result)
        rows.append(f"| {q['id']} | {'PASS' if b1_ok else 'FAIL'} ({n1}/{len(b1_claims)}) | "
                    f"{'PASS' if b2_ok else 'FAIL'} ({n2}/{len(b2_claims)}) |")
        runs.append({"id": q["id"], "question": q["question"], "b1": b1, "b2": {"sql": sql, "result": result[:4000], **b2},
                     "b1_unbacked": n1, "b2_unbacked": n2, "b1_missing": b1_miss, "b2_missing": b2_miss})
        print(rows[-1], flush=True)
    agent = (ROOT / "evals" / "results.md").read_text()
    agent_score = re.search(r"\*\*(\d+/\d+) passed", agent).group(1)
    md = ["# Baselines vs the agent", "",
          f"Same 6 questions, same pass rule (expected facts must appear in the answer's claims), same model "
          f"(`{llm.model}`), same local data mirror.", "",
          "| | passed | what it is |", "|---|---|---|",
          f"| **ExplainWhy agent** | **{agent_score}** | hypotheses → SQL steps → critic + repair; only critic-verified claims count ([results](results.md)) |",
          f"| B2 one-shot text-to-SQL | {score['B2']}/{len(questions)} | one query, answer from its rows, no critic |",
          f"| B1 Nemotron alone | {score['B1']}/{len(questions)} | schema only, no data access |", "",
          "Per question. In brackets: claims stating a 4+-digit number (year, value, code) that no query result "
          "backs, out of all claims. B1 never sees data, so every such number is unbacked.", "",
          "| question | B1 alone | B2 text-to-SQL |", "|---|---|---|", *rows, "",
          "The agent's answers contain no unbacked numbers by construction: its critic rejects any claim whose "
          "numbers are not in the cited rows. Raw baseline replies: `baseline_runs.json`."]
    (ROOT / "evals" / "baseline.md").write_text("\n".join(md) + "\n")
    (ROOT / "evals" / "baseline_runs.json").write_text(json.dumps(runs, indent=2))
    print(score)


if __name__ == "__main__":
    main()
