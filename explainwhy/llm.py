"""OpenAI-compatible chat client for NVIDIA Nemotron (served by Nebius Token Factory).

Every live reply is recorded under samples/llm_cache/, keyed by a hash of the
request, so SAMPLE_MODE can replay a run when the API is down.
"""
import hashlib
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self, replay: bool | None = None, timeout: int = 120, retries: int = 2):
        self.base_url = config.env("LLM_BASE_URL").rstrip("/")
        self.model = config.env("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b")
        self._key = config.env("LLM_API_KEY")
        self.replay = config.SAMPLE_MODE if replay is None else replay
        self.timeout, self.retries = timeout, retries
        self.calls = self.prompt_tokens = self.completion_tokens = 0
        if not self.replay and not (self.base_url and self._key):
            raise LLMError("Set LLM_BASE_URL and LLM_API_KEY in .env, or run with SAMPLE_MODE=true.")

    def _cache_path(self, messages: list[dict]):
        key = hashlib.sha256(json.dumps([self.model, messages], sort_keys=True).encode()).hexdigest()[:20]
        return config.LLM_CACHE_DIR / f"{key}.json"

    def chat(self, messages: list[dict], max_tokens: int = 2000) -> str:
        path = self._cache_path(messages)
        if self.replay:
            if not path.is_file():
                raise LLMError(f"SAMPLE_MODE: no recorded reply for this request ({path.name}). "
                               "Sample mode replays the three recorded sample questions only.")
            self.calls += 1
            return json.loads(path.read_text())["content"]
        body = {"model": self.model, "messages": messages, "temperature": 0, "max_tokens": max_tokens}
        last = None
        for attempt in range(self.retries + 1):
            try:
                req = Request(f"{self.base_url}/chat/completions", data=json.dumps(body).encode(), method="POST",
                              headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"})
                with urlopen(req, timeout=self.timeout) as r:
                    out = json.loads(r.read())
                break
            except (HTTPError, URLError, TimeoutError, OSError) as e:
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise LLMError(f"LLM call failed after {self.retries + 1} attempts: {last}")
        content = strip_reasoning(out["choices"][0]["message"].get("content") or "")
        usage = out.get("usage") or {}
        self.calls += 1
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        config.LLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": self.model, "content": content}, indent=1))
        return content

    def chat_json(self, messages: list[dict], max_tokens: int = 2000) -> dict:
        """Ask for JSON; one repair turn (asking for a shorter object) if the reply does not parse."""
        reply = self.chat(messages, max_tokens)
        try:
            return parse_json(reply)
        except ValueError as e:
            fix = messages + [{"role": "assistant", "content": reply},
                              {"role": "user", "content": f"That was not valid JSON ({e}); it may have been cut off. "
                                             "Reply with a shorter JSON object only."}]
            return parse_json(self.chat(fix, max_tokens))


def strip_reasoning(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    try:  # first complete object; ignores any trailing prose
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except json.JSONDecodeError as e:
        raise ValueError(str(e)) from e
