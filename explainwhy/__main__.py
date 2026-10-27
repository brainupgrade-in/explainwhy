"""CLI: python -m explainwhy "Why ...?"  [--zetaris]"""
import argparse
import sys

from .agent import Investigation
from .data import open_source

SAMPLES = [
    "Why does Apple's revenue history under the us-gaap Revenues concept stop at fiscal year 2018?",
    "Why does IBM drop out when EDGAR company profiles are joined to the company_dns SIC reference list?",
    "Why does Tesla report revenue under two different XBRL concepts, and which one should be used for which years?",
]


def main() -> None:
    p = argparse.ArgumentParser(prog="explainwhy", description=__doc__)
    p.add_argument("question", nargs="?", help="a bounded 'why' question (default: sample 1)")
    p.add_argument("--sample", type=int, choices=[1, 2, 3], help="run one of the three sample questions")
    p.add_argument("--zetaris", action="store_true", help="query the live Zetaris instance (falls back to local mirror)")
    a = p.parse_args()
    question = a.question or SAMPLES[(a.sample or 1) - 1]
    source, note = open_source(prefer_zetaris=a.zetaris)
    r = Investigation(question, source, note).run()
    print("\n" + "=" * 72 + f"\n{r['summary']}\n")
    for c in r["verified_claims"]:
        print(f"  ✓ {c['text']}  [{', '.join(c['evidence'])}]")
    for x in r["inferences"]:
        print(f"  ~ (inference, not proven by data) {x.get('text')}")
    for c in r["unverified_claims"]:
        print(f"  ✗ (dropped by critic) {c['text']}")
    sys.exit(0 if r["verified_claims"] else 1)


if __name__ == "__main__":
    main()
