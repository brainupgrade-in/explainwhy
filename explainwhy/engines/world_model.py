"""Meterless World Model engine, minimal Python implementation.

Event-sourced shared state for one investigation: every change is an
append-only event; current state is a fold over the log. Entities get stable,
content-derived IDs; ingest is idempotent (same idempotency key = no-op); every
event carries a monotonically increasing version so concurrent writers can
detect a lost update (expected_version check).
"""
import hashlib
import json
import time
from pathlib import Path


def stable_id(prefix: str, *parts: str) -> str:
    norm = "|".join(" ".join(p.lower().split()) for p in parts)
    return f"{prefix}-{hashlib.sha1(norm.encode()).hexdigest()[:6]}"


class VersionConflict(RuntimeError):
    pass


class WorldModel:
    def __init__(self, log_path: Path):
        self.path = log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []
        self._seen: set[str] = set()
        if self.path.is_file():
            for line in self.path.read_text().splitlines():
                ev = json.loads(line)
                self.events.append(ev)
                self._seen.add(ev["idem"])

    @property
    def version(self) -> int:
        return len(self.events)

    def emit(self, type_: str, entity: str, payload: dict, actor: str, idem: str | None = None,
             expected_version: int | None = None) -> dict | None:
        idem = idem or f"{type_}:{entity}:{json.dumps(payload, sort_keys=True, default=str)}"
        if idem in self._seen:
            return None  # idempotent re-ingest
        if expected_version is not None and expected_version != self.version:
            raise VersionConflict(f"expected v{expected_version}, at v{self.version}")
        ev = {"v": self.version + 1, "ts": round(time.time(), 3), "type": type_, "entity": entity,
              "actor": actor, "idem": idem, "payload": payload}
        self.events.append(ev)
        self._seen.add(idem)
        with self.path.open("a") as f:
            f.write(json.dumps(ev, default=str) + "\n")
        return ev

    def state(self) -> dict:
        s = {"question": None, "hypotheses": {}, "evidence": {}, "claims": {}, "answer": None}
        for ev in self.events:
            p, e = ev["payload"], ev["entity"]
            match ev["type"]:
                case "question_set":
                    s["question"] = p["text"]
                case "hypothesis_proposed":
                    s["hypotheses"].setdefault(e, {"text": p["text"], "status": "open", "evidence": []})
                case "hypothesis_updated":
                    h = s["hypotheses"].setdefault(e, {"text": p.get("text", ""), "status": "open", "evidence": []})
                    h["status"] = p["status"]
                    h["why"] = p.get("why", h.get("why", ""))
                    h["evidence"] = sorted(set(h["evidence"]) | set(p.get("evidence", [])))
                case "evidence_recorded":
                    s["evidence"][e] = p
                case "claim_checked":
                    s["claims"][e] = p
                case "answer_set":
                    s["answer"] = p
        return s
