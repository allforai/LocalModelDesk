"""Sampling defaults come from the model's own generation_config.json (2026-09-15 real-app loop)."""
import json

from desk.llm.sampling import FALLBACK_SAMPLING, model_sampling_defaults


def _config(tmp_path, payload):
    (tmp_path / "generation_config.json").write_text(
        payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return tmp_path


def test_uses_the_models_recommended_sampling(tmp_path):
    model = _config(tmp_path, {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "eos_token_id": [1]})
    assert model_sampling_defaults(model) == {"temperature": 1.0, "top_p": 0.95, "top_k": 20}


def test_fills_keys_the_model_leaves_out_from_the_fallback(tmp_path):
    """GLM 4.7 Flash only sets temperature 1.0. Measured on the real app 2026-09-15 with the
    same prompt: temperature alone ran to the token limit without an answer in 2 of 3 runs;
    adding top_p 0.95 answered in 3 of 3."""
    model = _config(tmp_path, {"temperature": 1.0})
    assert model_sampling_defaults(model) == {"temperature": 1.0, "top_p": 0.95}
    assert model_sampling_defaults(_config(tmp_path, {"temperature": 0.6, "top_p": 0.9})) == {"temperature": 0.6, "top_p": 0.9}


def test_falls_back_when_the_model_says_nothing_usable(tmp_path):
    assert FALLBACK_SAMPLING == {"temperature": 0.7, "top_p": 0.95}
    assert model_sampling_defaults(tmp_path) == FALLBACK_SAMPLING
    assert model_sampling_defaults(_config(tmp_path, "{not json")) == FALLBACK_SAMPLING
    assert model_sampling_defaults(_config(tmp_path, {"eos_token_id": 3})) == FALLBACK_SAMPLING
    assert model_sampling_defaults(_config(tmp_path, {"temperature": "hot", "top_k": True})) == FALLBACK_SAMPLING
    assert model_sampling_defaults(tmp_path / "missing-dir") == FALLBACK_SAMPLING
