"""Run the eval set (evals/questions.json) live and write evals/results.md.

A question passes when the run ends with at least one critic-verified claim and every expected
pattern matches at least one verified claim. Each question runs with an empty memory.

    python3 scripts/run_eval.py [--zetaris]     (--zetaris writes evals/results-zetaris.md and evals/runs-zetaris/)
"""
import json
import re
import shutil
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
    live = "--zetaris" in sys.argv
    source, note = open_source(prefer_zetaris=live)
    if live and source.name != "zetaris-rest":
        sys.exit(f"--zetaris requested but {note}")
    suffix = "-zetaris" if live else ""
    rows, passed = [], 0
    out_dir = ROOT / "evals" / f"runs{suffix}"
    out_dir.mkdir(parents=True, exist_ok=True)
    for q in questions:
        config.MEMORY_DIR = Path(tempfile.mkdtemp())
        inv = Investigation(q["question"], source, note, log=lambda *_: None)
        r = inv.run()
        claims = [c["text"] for c in r["verified_claims"]]
        missing = [p for p in q["expect"] if not any(re.search(p, c, re.I) for c in claims)]
        ok = bool(claims) and not missing
        passed += ok
        (out_dir / f"{q['id']}.json").write_text(json.dumps(r, indent=2, default=str))
        run_copy = out_dir / q["id"]  # full trace, so the replay page can show the run
        run_copy.mkdir(exist_ok=True)
        for f in ("report.md", "result.json", "events.jsonl", "trace.log"):
            shutil.copy(inv.run_dir / f, run_copy / f)
        rows.append(f"| {q['id']} | {'PASS' if ok else 'FAIL'} | {len(claims)} | {len(r['unverified_claims'])} | "
                    f"{r['critic_rounds']} | {r['elapsed_s']} | {', '.join(missing) or '-'} |")
        print(rows[-1], flush=True)
    md = [f"# Eval results", "", f"Backend: {source.name}. Model: {r['model']}. "
          f"**{passed}/{len(questions)} passed.**", "",
          "A question passes when at least one claim survives the critic and every expected pattern "
          "(see `questions.json`) matches a verified claim. Each question ran with an empty memory.", "",
          "| question | result | verified | dropped | critic rounds | seconds | missing patterns |",
          "|---|---|---|---|---|---|---|", *rows, "", f"Full results: `evals/runs{suffix}/<id>/`."]
    (ROOT / "evals" / f"results{suffix}.md").write_text("\n".join(md) + "\n")
    print(f"{passed}/{len(questions)} passed")


if __name__ == "__main__":
    main()
