"""Install the same pinned composite image model used by the Resources page."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desk.media.image_model import BASE, PROVENANCE, files, prepare_destination, validate_model
from desk.resources.fetch_cli import main as fetch_main
from desk.resources.parts import attempt_manifest_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    try:
        prepare_destination(root)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    manifest = attempt_manifest_path(root)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"repo": BASE, "files": files(), "image_provenance": PROVENANCE}))
    code = fetch_main(["download", BASE, "--local-dir", str(root), "--manifest", str(manifest)])
    if code:
        raise RuntimeError("下载失败；再次执行此命令可从已保存的 .part 文件继续")
    validate_model(root)
    print(f"Ready: {root}", flush=True)


if __name__ == "__main__":
    main()
