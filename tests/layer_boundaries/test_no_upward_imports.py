from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

SKYNETRA_ROOT = Path(__file__).resolve().parent.parent.parent / "skynetra"

LAYER_ORDER = {
    "foundation": 0,
    "domain": 1,
    "engines": 2,
    "orchestration": 3,
    "interface": 4,
}

LAYER_PREFIXES: dict[str, int] = {}
for name, order in LAYER_ORDER.items():
    LAYER_PREFIXES[f"skynetra.{name}"] = order


def _get_layer_level(file_path: Path) -> int | None:
    rel = file_path.relative_to(SKYNETRA_ROOT)
    parts = rel.parts
    for p in parts:
        if p in LAYER_ORDER:
            return LAYER_ORDER[p]
    return None


def _extract_imports(file_path: Path) -> list[tuple[str, int]]:
    with open(file_path) as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                imports.append((top, node.lineno))
    return imports


def test_no_upward_imports():
    errors: list[str] = []
    for py_file in sorted(SKYNETRA_ROOT.rglob("*.py")):
        src_level = _get_layer_level(py_file)
        if src_level is None:
            continue
        for top_module, lineno in _extract_imports(py_file):
            if top_module == "skynetra":
                continue
            dst_level = None
            for prefix, level in LAYER_PREFIXES.items():
                if top_module == prefix.split(".")[-1]:
                    dst_level = level
                    break
            if dst_level is not None and dst_level > src_level:
                errors.append(
                    f"{py_file.relative_to(SKYNETRA_ROOT)}:{lineno} imports "
                    f"'{top_module}' (layer {dst_level}) from layer {src_level}"
                )
    assert not errors, "\n".join(errors)


@pytest.mark.skipif(
    not sys.version_info >= (3, 11), reason="import-linter requires Python 3.11+"
)
def test_import_linter_via_subprocess():
    try:
        result = subprocess.run(
            ["import-linter", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        has_inter = result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        has_inter = False

    if not has_inter:
        pytest.skip("import-linter not installed")

    result = subprocess.run(
        ["import-linter", "lint", "--config",
         str(SKYNETRA_ROOT.parent / ".importlinter")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"import-linter violations:\n{result.stdout}\n{result.stderr}"
