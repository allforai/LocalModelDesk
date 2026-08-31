"""music3_cli smoke tests that do not load the MLX pipeline."""
import ast
import subprocess
import sys
from pathlib import Path


CLI = Path(__file__).resolve().parent.parent / "desk" / "media" / "music3_cli.py"


def test_help_runs_without_mlx_pipeline():
    res = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0
    for flag in ("--root", "--caption", "--lyrics", "--duration", "--output"):
        assert flag in res.stdout


def test_missing_required_args_fail_nonzero():
    res = subprocess.run(
        [sys.executable, str(CLI), "--caption", "x"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode != 0


def test_module_top_imports_only_argparse():
    tree = ast.parse(CLI.read_text(encoding="utf-8"))
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    assert names <= {"argparse"}


def test_never_calls_unload_or_imports_desk():
    src = CLI.read_text(encoding="utf-8")
    assert "unload-llm" not in src
    assert "import desk" not in src
    assert "sys.exit(" not in src
    assert "SystemExit" not in src
