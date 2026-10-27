"""Meterless Markovian engine, minimal Python implementation.

A long investigation runs as a chain of bounded steps. Each step's prompt holds
only the truncated goal, the structured carryover block
(COMPLETED / REMAINING / DECISIONS / CONTEXT) and the latest observation --
never the full transcript -- so cost per step stays flat. The model ends each
step with one marker: [NEEDS_TOOL] (host runs a query and resumes),
[STATE_CHECKPOINT] (new carryover) or [TASK_COMPLETE].
"""
from dataclasses import dataclass, field

CARRYOVER_KEYS = ("COMPLETED", "REMAINING", "DECISIONS", "CONTEXT")


@dataclass
class ChunkConfig:
    max_chunks: int = 8
    carryover_tokens: int = 800

    def __post_init__(self):
        if not 1 <= self.max_chunks <= 32:
            raise ValueError("max_chunks must be 1..32")
        if not 128 <= self.carryover_tokens <= 32768:
            raise ValueError("carryover_tokens must be 128..32768")


def est_tokens(text: str) -> int:
    return -(-len(text) // 4)  # ceil(chars/4), as in the spec


def carryover_block(c: dict, budget_tokens: int) -> str:
    text = "\n".join(f"{k}: {str(c.get(k, '')).strip() or '-'}" for k in CARRYOVER_KEYS)
    if est_tokens(text) > budget_tokens:  # absolute fallback: tail-truncate to budget
        text = text[: budget_tokens * 4]
    return text


def compress_heuristic(prev: dict, observation: str) -> dict:
    """Fallback when the model returns no usable carryover: keep the old block, append the latest observation."""
    out = dict(prev) if prev else {k: "" for k in CARRYOVER_KEYS}
    out["CONTEXT"] = (str(out.get("CONTEXT", "")) + f" | last observation: {observation[:300]}").strip(" |")
    return out


@dataclass
class MarkovianRun:
    config: ChunkConfig
    goal: str
    carryover: dict = field(default_factory=lambda: {k: "" for k in CARRYOVER_KEYS})
    chunks: list = field(default_factory=list)  # per-step records
    status: str = "running"

    def prompt_context(self, observation: str) -> str:
        goal = self.goal if len(self.goal) <= 200 else self.goal[:197] + "..."
        return (f"GOAL: {goal}\n\n[CARRYOVER]\n{carryover_block(self.carryover, self.config.carryover_tokens)}\n\n"
                f"[LATEST OBSERVATION]\n{observation or '(none yet)'}")

    def record(self, marker: str, prompt: str, output: str, new_carryover: dict | None, observation: str) -> None:
        if new_carryover and len(carryover_block(new_carryover, 10_000)) >= 24:
            self.carryover = {k: new_carryover.get(k, "") for k in CARRYOVER_KEYS}
        else:
            self.carryover = compress_heuristic(self.carryover, observation)
        self.chunks.append({"id": len(self.chunks) + 1, "marker": marker, "prompt_tokens": est_tokens(prompt),
                            "output_tokens": est_tokens(output), "carryover": dict(self.carryover)})

    def stats(self) -> dict:
        """Tokens sent vs. what a full-transcript loop would have sent (each step re-sending all prior output)."""
        used = sum(c["prompt_tokens"] for c in self.chunks)
        full, history = 0, 0
        for c in self.chunks:
            full += c["prompt_tokens"] + history
            history += c["output_tokens"] + c["prompt_tokens"] // 2
        saved = max(0, full - used)
        return {"steps": len(self.chunks), "prompt_tokens_used": used, "full_transcript_estimate": full,
                "tokens_saved": saved, "efficiency_percent": round(100 * saved / full, 1) if full else 0.0,
                "status": self.status}
