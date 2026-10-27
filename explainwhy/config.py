"""Settings from the environment, with a repo-root .env loaded first (values never logged)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


SAMPLE_MODE = env("SAMPLE_MODE").lower() in ("1", "true", "yes")
RUN_DEADLINE_S = int(env("RUN_DEADLINE_S", "480"))  # whole run, hard stop
MAX_STEPS = int(env("MAX_STEPS", "8"))  # investigation steps per round
MAX_REPAIR_ROUNDS = int(env("MAX_REPAIR_ROUNDS", "2"))  # critic -> investigator loops
DATA_DIR = ROOT / "data"
LLM_CACHE_DIR = ROOT / "samples" / "llm_cache"
MEMORY_DIR = Path(env("MEMORY_DIR", str(ROOT / "memory")))
RUNS_DIR = ROOT / "runs"
