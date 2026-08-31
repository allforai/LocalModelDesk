#!/usr/bin/env python3
"""RG-1 helper for a read-only scan of a real models tree and disk usage.

This may be slow and depends on real disk state, so it is for human use only:

    python3 scripts/verify_real_models.py --models-root /Users/aa/LocalModelDesk \
        --data-root /tmp/lmd-rg1 --refresh
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desk.resources.service import ResourcesService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models-root",
        required=True,
        help="Real model root containing llms/, minimax-h3/, and minimax-music3/.",
    )
    parser.add_argument(
        "--data-root",
        default=None,
        help="Manifest cache directory; defaults to a temporary directory.",
    )
    parser.add_argument("--refresh", action="store_true", help="Fetch fresh HF manifests.")
    args = parser.parse_args()

    data_root = Path(args.data_root or tempfile.mkdtemp(prefix="lmd-rg1-"))
    roots = SimpleNamespace(
        models_root=Path(args.models_root).resolve(),
        data_root=data_root,
        hf_cmd=(),
    )
    service = ResourcesService(
        resolve_paths=lambda: roots,
        can_start_heavy=lambda: {"ok": True},
    )
    statuses = service.verify_all_models(refresh=args.refresh)
    disk = service.disk_usage()
    print(
        json.dumps(
            {"models": [status.to_json() for status in statuses], "disk": disk.to_json()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
