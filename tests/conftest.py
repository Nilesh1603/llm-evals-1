import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402


def _load_jsonl(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.fixture(scope="session")
def golden_set() -> list[dict]:
    return _load_jsonl(ROOT / "golden_set" / "golden_set.jsonl")


@pytest.fixture(scope="session")
def model_outputs() -> dict[str, str]:
    rows = _load_jsonl(ROOT / "golden_set" / "model_outputs.jsonl")
    return {row["id"]: row["model_output"] for row in rows}


@pytest.fixture(scope="session")
def golden_by_id(golden_set) -> dict[str, dict]:
    return {row["id"]: row for row in golden_set}
