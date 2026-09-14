import wave

from desk.media.audio import wav_seconds


def test_wav_seconds_reads_the_real_length(tmp_path):
    path = tmp_path / "a.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        out.writeframes(b"\x00\x00" * 8000 * 3)
    assert wav_seconds(path) == 3.0


def test_wav_seconds_is_none_for_non_wav(tmp_path):
    path = tmp_path / "a.wav"
    path.write_bytes(b"fake-media-bytes")
    assert wav_seconds(path) is None
    assert wav_seconds(tmp_path / "missing.wav") is None
