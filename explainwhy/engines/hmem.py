"""Meterless H-MEM engine, minimal Python implementation.

Plain-file memory (memories.jsonl, greppable) with mandatory source +
provenance, the H-MEM hybrid retrieval score (no embeddings here: the semantic
term reuses keyword overlap), supersession instead of deletion, feedback
adaptation with the spec's exact deltas, and an append-only audit ledger.
"""
import json
import math
import re
import time
from pathlib import Path

from .world_model import stable_id

LAYER_WEIGHT = {"long_term": 1.0, "working": 0.8, "short_term": 0.6}
STOP = set("the a an of to in for and or is are was were why does did do what how on at by with from its it as be".split())


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 1}


class HMem:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.mem_path, self.audit_path = root / "memories.jsonl", root / "audit.jsonl"
        self.records: dict[str, dict] = {}
        if self.mem_path.is_file():
            for line in self.mem_path.read_text().splitlines():
                r = json.loads(line)
                self.records[r["id"]] = r  # last write wins

    def _save(self, rec: dict) -> None:
        self.records[rec["id"]] = rec
        with self.mem_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")

    def _audit(self, memory_id: str, action: str, actor: str, **details) -> None:
        with self.audit_path.open("a") as f:
            f.write(json.dumps({"memoryId": memory_id, "action": action, "actor": actor,
                                "timestamp": time.time(), "details": details}) + "\n")

    def write(self, content: str, source: str, confidence: float, entities: list[str], tags: list[str],
              provenance_label: str, refs: list[str], actor: str, mission_id: str, key: str | None = None) -> dict:
        if not source:
            raise ValueError("H-MEM: a memory without a source is rejected by construction")
        now = time.time()
        mid = stable_id("M", key or content)
        old = self.records.get(mid)
        rec = {"id": mid, "content": content, "type": "factual", "layer": "working", "timestamp": now,
               "lastAccessed": now, "accessCount": 0, "tags": tags, "confidence": round(confidence, 2),
               "source": source, "entities": entities[:10], "domain": "sec-edgar", "missionId": mission_id,
               "provenance": {"origin": "agent_verified_claim", "learnedAt": now, "label": provenance_label, "refs": refs},
               "supersedes": None, "supersededBy": None}
        if old and old["content"] != content:
            # Same key, new content: keep both, newest wins retrieval (conflict -> supersede, never delete).
            old_id = stable_id("M", f"{mid}@{old['timestamp']}")
            self._save({**old, "id": old_id, "supersededBy": mid})
            rec["supersedes"] = old_id
            self._audit(mid, "conflict_resolved", actor, superseded=old_id)
        if old and old["content"] == content:
            rec = {**old, "confidence": max(old["confidence"], rec["confidence"]), "lastAccessed": now}
            self._audit(mid, "update", actor, reason="re-verified")
        else:
            self._audit(mid, "create", actor, source=source)
        self._save(rec)
        return rec

    def retrieve(self, query: str, entities: list[str] = (), top_n: int = 5, threshold: float = 0.35) -> list[dict]:
        q = tokens(query)
        q_top = set(sorted(q)[:8]) if len(q) > 8 else q
        q_ents = {e.lower() for e in entities} | q
        now, scored = time.time(), []
        for r in self.records.values():
            m = tokens(r["content"] + " " + " ".join(r["tags"]))
            kw = len(q_top & m) / len(q_top | m) if (q_top | m) else 0.0
            sem = len(q & m) / len(q) if q else 0.0  # stand-in for embedding similarity
            tag = 1.0 if q & {t.lower() for t in r["tags"]} else 0.0
            ent = 1.0 if q_ents & {e.lower() for e in r["entities"]} else 0.0
            recency = math.exp(-(now - r["lastAccessed"]) / (14 * 86400))
            raw = (0.35 * sem + 0.20 * kw + 0.10 * tag + 0.10 * 1.0 + 0.15 * ent
                   + 0.05 * LAYER_WEIGHT[r["layer"]] + 0.05 * recency - 0.20 * (1 if r["supersededBy"] else 0))
            score = max(0.0, min(1.0, raw)) * r["confidence"]
            if score >= threshold:
                scored.append({**r, "score": round(score, 3)})
        hits = sorted(scored, key=lambda r: -r["score"])[:top_n]
        for h in hits:
            self._audit(h["id"], "read", "retriever", score=h["score"], query=query[:120])
        return hits

    def feedback(self, memory_id: str, verdict: str, actor: str) -> None:
        r = dict(self.records[memory_id])
        delta = {"helpful": 0.05, "not_helpful": -0.03, "wrong": -0.20}[verdict]
        r["confidence"] = round(max(0.0, min(1.0, r["confidence"] + delta)), 2)
        if verdict == "helpful":
            r["accessCount"] += 1
        if verdict == "wrong":
            r["tags"] = sorted(set(r["tags"]) | {"review"})
        self._save(r)
        self._audit(memory_id, "feedback", actor, verdict=verdict, confidence=r["confidence"])

    @staticmethod
    def reinjection_block(hits: list[dict]) -> str:
        if not hits:
            return "(no prior findings in memory)"
        lines = ["[domain: sec-edgar] prior verified findings -- re-check with a query before relying on them:"]
        for h in hits:
            lines.append(f"- ({h['layer']}, conf {h['confidence']}, score {h['score']}, id {h['id']}) {h['content']}"
                         f"  [source: {h['source']}]")
        return "\n".join(lines)
