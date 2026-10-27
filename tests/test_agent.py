import json

import pytest

from explainwhy import config
from explainwhy.agent import Investigation, numbers_in
from explainwhy.data import LocalSource, SQLRejected, guard
from explainwhy.engines.hmem import HMem
from explainwhy.engines.markovian import ChunkConfig, MarkovianRun
from explainwhy.engines.world_model import VersionConflict, WorldModel, stable_id

Q = "Why does Apple's revenue history under Revenues stop at fiscal year 2018?"
SQL_COUNT = ("SELECT concept, MAX(fiscal_year) AS last_fy, COUNT(*) AS n FROM edgar.revenue_facts "
             "WHERE cik = 320193 GROUP BY concept")
E_COUNT = stable_id("E", guard(SQL_COUNT))


class FakeLLM:
    """Replays a fixed script of replies; records the prompts it was sent."""
    model, replay = "fake", True

    def __init__(self, replies, summary="Apple's Revenues concept ends in fiscal year 2018."):
        self.replies, self.calls, self.sent, self.summary = list(replies), 0, [], summary

    def chat_json(self, messages, max_tokens=2000):
        self.sent.append(messages)
        self.calls += 1
        if messages[0]["content"].startswith("You write the final answer"):
            return {"summary": self.summary}
        return self.replies.pop(0)


def plan():
    return {"hypotheses": [{"text": "Apple switched to the ASC 606 revenue concept", "how_to_test": "compare concepts"},
                           {"text": "Apple stopped filing after 2018", "how_to_test": "check later filings"}]}


def finish(claim_text, evidence):
    return {"marker": "TASK_COMPLETE", "answer": {"summary": "Apple moved to the ASC 606 concept.",
                                                  "claims": [{"text": claim_text, "evidence": evidence}],
                                                  "hypothesis_verdicts": VERDICTS}}


H1, H2 = stable_id("H", plan()["hypotheses"][0]["text"]), stable_id("H", plan()["hypotheses"][1]["text"])
VERDICTS = [{"id": H1, "status": "supported", "evidence": [E_COUNT]}, {"id": H2, "status": "refuted", "evidence": [E_COUNT]}]


def test_finish_bounced_once_when_hypotheses_lack_verdicts(tmp_path):
    no_verdicts = finish("Apple has 117 ASC 606 facts.", [E_COUNT])
    no_verdicts["answer"]["hypothesis_verdicts"] = []
    r, llm, inv = run([plan(), {"marker": "NEEDS_TOOL", "sql": SQL_COUNT, "purpose": "compare"}, no_verdicts,
                       finish("Apple has 117 ASC 606 facts.", [E_COUNT]),
                       {"claims": [{"index": 0, "verdict": "supported", "reason": "ok"}]}], tmp_path)
    assert "have no verdict" in llm.sent[3][-1]["content"]
    assert {v["status"] for v in r["hypotheses"].values()} == {"supported", "refuted"}


def test_zero_result_with_nonexistent_filter_value_is_rejected(tmp_path):
    vacuous = "SELECT COUNT(*) AS n FROM edgar.revenue_facts WHERE entity_name = 'Apple' AND fiscal_year > 2018"
    e_vac = stable_id("E", guard(vacuous))
    r, llm, inv = run([plan(), {"marker": "NEEDS_TOOL", "sql": vacuous, "purpose": "absence"},
                       finish("Apple has no Revenues rows after fiscal year 2018.", [e_vac]),
                       {"marker": "NEEDS_TOOL", "sql": SQL_COUNT, "purpose": "compare"},
                       finish("Apple's Revenues concept ends in fiscal year 2018.", [E_COUNT]),
                       {"claims": [{"index": 0, "verdict": "supported", "reason": "ok"}]}], tmp_path)
    assert "entity_name = 'Apple'" in llm.sent[3][-1]["content"]  # repair prompt names the vacuous filter
    assert [c["evidence"] for c in r["verified_claims"]] == [[E_COUNT]]


@pytest.fixture(autouse=True)
def tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MEMORY_DIR", tmp_path / "memory")
    monkeypatch.setattr(config, "MAX_STEPS", 4)
    monkeypatch.setattr(config, "MAX_REPAIR_ROUNDS", 1)
    return tmp_path


def run(replies, tmp_path, **kw):
    llm = FakeLLM(replies, **kw)
    inv = Investigation(Q, LocalSource(), "test", llm=llm, run_dir=tmp_path / "run", log=lambda *_: None)
    return inv.run(), llm, inv


def test_guard_blocks_writes_and_caps_rows():
    for bad in ["DROP TABLE edgar.revenue_facts", "SELECT 1; DELETE FROM x", "UPDATE x SET a=1"]:
        with pytest.raises(SQLRejected):
            guard(bad)
    assert guard("SELECT 1").endswith("LIMIT 200")


def test_verified_claim_end_to_end(tmp_path):
    claim = "Apple's Revenues concept has 11 facts ending in fiscal year 2018, while the ASC 606 concept has 117."
    r, llm, inv = run([plan(), {"marker": "NEEDS_TOOL", "sql": SQL_COUNT, "purpose": "compare concepts", "tests": []},
                       finish(claim, [E_COUNT]),
                       {"claims": [{"index": 0, "verdict": "supported", "reason": "rows show it"}]}], tmp_path)
    assert [c["text"] for c in r["verified_claims"]] == [claim]
    assert r["memories_written"] == 1 and r["critic_rounds"] == 1
    events = [json.loads(l)["type"] for l in (tmp_path / "run" / "events.jsonl").read_text().splitlines()]
    assert events[:2] == ["question_set", "hypothesis_proposed"] and "evidence_recorded" in events
    assert (tmp_path / "run" / "report.md").read_text().count(E_COUNT) >= 2


def test_critic_rejects_number_not_in_evidence_then_repairs(tmp_path):
    wrong = "Apple's Revenues concept has 11 facts ending in fiscal year 2021."
    right = "Apple's Revenues concept has 11 facts ending in fiscal year 2018."
    r, llm, inv = run([plan(), {"marker": "NEEDS_TOOL", "sql": SQL_COUNT, "purpose": "compare", "tests": []},
                       finish(wrong, [E_COUNT]),  # deterministic check fails: 2021 is not in rows -> no LLM critic call
                       finish(right, [E_COUNT]),  # repair round
                       {"claims": [{"index": 0, "verdict": "supported", "reason": "ok"}]}], tmp_path)
    assert r["critic_rounds"] == 2
    assert [c["text"] for c in r["verified_claims"]] == [right]
    repair_prompt = llm.sent[3][-1]["content"]
    assert "CRITIC FEEDBACK" in repair_prompt and "2021" in repair_prompt


def test_cannot_finish_without_evidence(tmp_path):
    r, llm, inv = run([plan(), finish("Apple changed concepts.", []),
                       {"marker": "NEEDS_TOOL", "sql": SQL_COUNT, "purpose": "compare", "tests": []},
                       finish("Apple has 117 ASC 606 facts.", [E_COUNT]),
                       {"claims": [{"index": 0, "verdict": "supported", "reason": "ok"}]}], tmp_path)
    assert "cannot finish without evidence" in llm.sent[2][-1]["content"]
    assert len(r["verified_claims"]) == 1


def test_sql_error_is_fed_back_for_repair(tmp_path):
    r, llm, inv = run([plan(), {"marker": "NEEDS_TOOL", "sql": "SELECT nope FROM edgar.revenue_facts", "purpose": "x"},
                       {"marker": "NEEDS_TOOL", "sql": SQL_COUNT, "purpose": "compare"},
                       finish("Apple has 117 ASC 606 facts.", [E_COUNT]),
                       {"claims": [{"index": 0, "verdict": "supported", "reason": "ok"}]}], tmp_path)
    assert "QUERY ERROR" in llm.sent[2][-1]["content"]
    assert r["verified_claims"]


def test_world_model_idempotent_and_versioned(tmp_path):
    wm = WorldModel(tmp_path / "e.jsonl")
    assert wm.emit("hypothesis_proposed", "H-1", {"text": "a"}, "p")
    assert wm.emit("hypothesis_proposed", "H-1", {"text": "a"}, "p") is None
    with pytest.raises(VersionConflict):
        wm.emit("hypothesis_updated", "H-1", {"status": "refuted"}, "p", expected_version=0)
    assert WorldModel(tmp_path / "e.jsonl").state()["hypotheses"]["H-1"]["text"] == "a"  # replay from log


def test_hmem_requires_source_supersedes_and_recalls(tmp_path):
    m = HMem(tmp_path / "mem")
    with pytest.raises(ValueError):
        m.write("x", source="", confidence=0.8, entities=[], tags=[], provenance_label="", refs=[], actor="t", mission_id="r")
    m.write("Apple Revenues concept ends at fiscal year 2018", "zetaris:E-1", 0.85, ["apple"], ["edgar", "apple"],
            "t", [], "t", "r", key="apple-revenues")
    m.write("Apple Revenues concept ends at FY2018; ASC 606 concept continues", "zetaris:E-2", 0.85, ["apple"],
            ["edgar", "apple"], "t", [], "t", "r", key="apple-revenues")
    hits = HMem(tmp_path / "mem").retrieve("why does apple revenues stop at 2018")
    assert hits and "ASC 606" in hits[0]["content"]
    assert sum(1 for r in m.records.values() if r["supersededBy"]) == 1
    m.feedback(hits[0]["id"], "wrong", "t")
    assert m.records[hits[0]["id"]]["confidence"] == 0.65 and "review" in m.records[hits[0]["id"]]["tags"]


def test_markovian_carryover_bounded_and_flat():
    mk = MarkovianRun(ChunkConfig(max_chunks=8, carryover_tokens=128), "goal " * 100)
    ctx = mk.prompt_context("obs")
    assert "GOAL:" in ctx and len(ctx.split("GOAL: ")[1].split("\n")[0]) <= 200
    for i in range(5):
        mk.record("NEEDS_TOOL", "p" * 4000, "o" * 2000, {"COMPLETED": f"step {i}", "REMAINING": "more"}, "obs")
    s = mk.stats()
    assert s["steps"] == 5 and s["tokens_saved"] > 0 and s["full_transcript_estimate"] > s["prompt_tokens_used"]


def test_numbers_in_ignores_short_numbers():
    assert numbers_in("FY2018 had 11 facts and $265,595,000,000") == {"2018", "265595000000"}


def test_summary_with_unverified_number_falls_back_to_claims(tmp_path):
    claim = "Apple's Revenues concept has 11 facts ending in fiscal year 2018, while the ASC 606 concept has 117."
    script = [plan(), {"marker": "NEEDS_TOOL", "sql": SQL_COUNT, "purpose": "compare"}, finish(claim, [E_COUNT]),
              {"claims": [{"index": 0, "verdict": "supported", "reason": "ok"}]}]
    r, _, _ = run(list(script), tmp_path / "a", summary="Apple filed 9999 facts.")
    assert r["summary"] == claim
    r, _, _ = run(list(script), tmp_path / "b", summary="Apple likely moved to ASC 606; the old concept ends in 2018.")
    assert r["summary"].startswith("Apple likely")
