"""R-llm-07: frontend cannot access port 8767; state.py owns its literal."""
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def test_default_port_importable_single_source():
    from desk.llm.state import DEFAULT_LLM_PORT

    assert DEFAULT_LLM_PORT == 8767


def test_static_frontend_never_mentions_llm_port():
    static_dir = REPO / "desk" / "static"
    if not static_dir.exists():
        return
    offenders = [
        str(path)
        for path in static_dir.rglob("*")
        if path.is_file() and "127.0.0.1:8767" in path.read_text(errors="ignore")
    ]
    assert offenders == [], f"frontend must not directly connect to mlx-lm: {offenders}"


def test_port_literal_only_defined_in_state_py():
    llm_dir = REPO / "desk" / "llm"
    offenders = [
        str(path)
        for path in llm_dir.glob("*.py")
        if path.name != "state.py" and "8767" in path.read_text(errors="ignore")
    ]
    assert offenders == [], f"8767 may only be defined in desk/llm/state.py: {offenders}"
