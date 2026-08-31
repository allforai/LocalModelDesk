"""Make the repo root importable so tests can `import desk.*` without an install."""
import sys
from pathlib import Path


_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
