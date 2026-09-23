"""The resumable fetcher keeps partial bytes across attempts (R-resources-06, cross-exam 2026-09-13 G4/J18)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from desk.resources import fetch_cli
from desk.resources.parts import attempt_manifest_path, part_bytes, part_path
from desk.resources.manifest import ManifestFile

BLOB = bytes(range(256)) * 40  # 10240 bytes


class _Server:
    """Serves BLOB at /org/repo/resolve/main/<anything>, honouring Range, recording headers."""

    def __init__(self, *, ignore_range=False, cut_after=None):
        self.ranges = []
        self.paths = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                outer.paths.append(self.path)
                header = self.headers.get("Range")
                outer.ranges.append(header)
                start = 0
                if header and not ignore_range:
                    start = int(header.removeprefix("bytes=").split("-")[0])
                body = BLOB[start:]
                self.send_response(206 if start else 200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if cut_after is not None and not header:
                    self.wfile.write(body[:cut_after])
                    self.wfile.flush()
                    self.connection.close()
                    return
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.endpoint = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def _manifest(tmp_path, files):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"repo": "org/repo", "files": [{"path": p, "size": s} for p, s in files]}))
    return path


def test_composite_download_uses_each_pinned_source_and_marks_complete(tmp_path):
    server = _Server()
    try:
        dest = tmp_path / "model"
        manifest = tmp_path / "composite.json"
        manifest.write_text(json.dumps({"files": [
            {"path": "transformer/a.bin", "size": len(BLOB), "repo": "base/repo", "revision": "base-rev", "source_path": "a.bin"},
            {"path": "text_encoder/b.bin", "size": len(BLOB), "repo": "heretic/repo", "revision": "encoder-rev", "source_path": "b.bin"}],
            "image_provenance": {"base_revision": "base-rev", "text_encoder_revision": "encoder-rev"}}))
        part = part_path(dest, "text_encoder/b.bin")
        part.parent.mkdir(parents=True)
        part.write_bytes(BLOB[:4000])
        assert fetch_cli.main(["download", "ignored/repo", "--local-dir", str(dest),
            "--manifest", str(manifest), "--endpoint", server.endpoint]) == 0
        assert server.paths == ["/base/repo/resolve/base-rev/a.bin", "/heretic/repo/resolve/encoder-rev/b.bin"]
        assert server.ranges == [None, "bytes=4000-"]
        assert json.loads((dest / "localmodeldesk-image.json").read_text())["complete"] is True
    finally:
        server.close()


def test_resume_sends_range_from_existing_part_and_moves_into_place(tmp_path):
    server = _Server()
    try:
        dest = tmp_path / "model"
        part = part_path(dest, "weights/a.bin")
        part.parent.mkdir(parents=True)
        part.write_bytes(BLOB[:4000])

        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("weights/a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint])

        assert code == 0
        assert server.ranges == ["bytes=4000-"]
        assert (dest / "weights/a.bin").read_bytes() == BLOB
        assert not part.exists()
    finally:
        server.close()


def test_server_ignoring_range_restarts_the_part_instead_of_appending(tmp_path):
    server = _Server(ignore_range=True)
    try:
        dest = tmp_path / "model"
        part = part_path(dest, "a.bin")
        part.parent.mkdir(parents=True)
        part.write_bytes(b"garbage!" * 10)

        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint])

        assert code == 0
        assert (dest / "a.bin").read_bytes() == BLOB
    finally:
        server.close()


def test_complete_final_file_is_not_requested_again(tmp_path):
    server = _Server()
    try:
        dest = tmp_path / "model"
        dest.mkdir()
        (dest / "a.bin").write_bytes(BLOB)

        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint])

        assert code == 0
        assert server.ranges == []
    finally:
        server.close()


def test_dropped_connection_keeps_bytes_then_retry_resumes(tmp_path):
    server = _Server(cut_after=3000)
    try:
        dest = tmp_path / "model"
        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB))])),
                               "--endpoint", server.endpoint], sleep=lambda _s: None)

        assert code == 0
        assert server.ranges[0] is None
        assert server.ranges[1] == "bytes=3000-"
        assert (dest / "a.bin").read_bytes() == BLOB
    finally:
        server.close()


def test_size_mismatch_fails_and_keeps_the_part(tmp_path, capsys):
    server = _Server()
    try:
        dest = tmp_path / "model"
        code = fetch_cli.main(["download", "org/repo", "--local-dir", str(dest),
                               "--manifest", str(_manifest(tmp_path, [("a.bin", len(BLOB) + 5)])),
                               "--endpoint", server.endpoint])

        assert code == 1
        assert "a.bin" in capsys.readouterr().err
        assert part_path(dest, "a.bin").stat().st_size == len(BLOB)
        assert not (dest / "a.bin").exists()
    finally:
        server.close()


def test_part_bytes_counts_only_incomplete_files_capped_at_expected(tmp_path):
    dest = tmp_path / "model"
    dest.mkdir()
    (dest / "done.bin").write_bytes(b"x" * 10)
    for rel, size in (("done.bin", 3), ("half.bin", 4), ("over.bin", 99)):
        part = part_path(dest, rel)
        part.parent.mkdir(parents=True, exist_ok=True)
        part.write_bytes(b"x" * size)
    files = (ManifestFile("done.bin", 10), ManifestFile("half.bin", 8), ManifestFile("over.bin", 20))
    assert part_bytes(dest, files) == 4 + 20
    assert attempt_manifest_path(dest) == dest / ".cache" / "localmodeldesk" / "manifest.json"


def test_fetch_cli_has_no_package_imports():
    source = Path(fetch_cli.__file__).read_text(encoding="utf-8")
    assert "from desk" not in source and "import desk" not in source and "from ." not in source
