from desk.media.memory_estimate import estimate_bytes

GIB = 1024 ** 3
DRAFT = {"width": 512, "height": 288, "frames": 49, "steps": 16}
SHARP = {"width": 1024, "height": 576, "frames": 73, "steps": 16}


def test_draft_matches_the_measured_peak():
    """实测 2026-09-08：草稿档 peak 27.0 GiB（evidence/q20、q24、q12 三份日志一致）。"""
    assert 25 * GIB <= estimate_bytes("video", DRAFT) <= 31 * GIB


def test_sharper_preset_estimates_more_than_draft():
    assert estimate_bytes("video", SHARP) > estimate_bytes("video", DRAFT)


def test_estimate_is_monotonic_in_every_dimension():
    base = estimate_bytes("video", DRAFT)
    for field in ("width", "height", "frames"):
        bigger = dict(DRAFT, **{field: DRAFT[field] * 2})
        assert estimate_bytes("video", bigger) > base


def test_music_has_its_own_baseline():
    assert estimate_bytes("music", {"duration": 10}) < 40 * GIB
