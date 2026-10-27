"""Run the eval set (evals/questions.json) live and write evals/results.md.

A question passes when the run ends with at least one critic-verified claim and every expected
pattern matches at least one verified claim. Each question runs with an empty memory.

    python3 scripts/run_eval.py [--zetaris]
"""
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from explainwhy import config  # noqa: E402
from explainwhy.agent import Investigation  # noqa: E402
from explainwhy.data import open_source  # noqa: E402


def main() -> None:
    questions = json.loads((ROOT / "evals" / "questions.json").read_text())
    config.LLM_CACHE_DIR = ROOT / "evals" / "llm_cache"  # keep eval replies apart from the sample-replay cache
    source, note = open_source(prefer_zetaris="--zetaris" in sys.argv)
    rows, passed = [], 0
    out_dir = ROOT / "evals" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    for q in questions:
        config.MEMORY_DIR = Path(tempfile.mkdtemp())
        r = Investigation(q["question"], source, note, log=lambda *_: None).run()
        claims = [c["text"] for c in r["verified_claims"]]
        missing = [p for p in q["expect"] if not any(re.search(p, c, re.I) for c in claims)]
        ok = bool(claims) and not missing
        passed += ok
        (out_dir / f"{q['id']}.json").write_text(json.dumps(r, indent=2, default=str))
        rows.append(f"| {q['id']} | {'PASS' if ok else 'FAIL'} | {len(claims)} | {len(r['unverified_claims'])} | "
                    f"{r['critic_rounds']} | {r['elapsed_s']} | {', '.join(missing) or '-'} |")
        print(rows[-1], flush=True)
    md = [f"# Eval results", "", f"Backend: {source.name}. Model: {r['model']}. "
          f"**{passed}/{len(questions)} passed.**", "",
          "A question passes when at least one claim survives the critic and every expected pattern "
          "(see `questions.json`) matches a verified claim. Each question ran with an empty memory.", "",
          "| question | result | verified | dropped | critic rounds | seconds | missing patterns |",
          "|---|---|---|---|---|---|---|", *rows, "", "Full results: `evals/runs/<id>.json`."]
    (ROOT / "evals" / "results.md").write_text("\n".join(md) + "\n")
    print(f"{passed}/{len(questions)} passed")


if __name__ == "__main__":
    main()
