"""
Layer 4 boundary sanity check: `skynetra.interface` is the ONLY package
allowed by import-linter to import from all of layer0-layer3.

This test mirrors the `.importlinter` layers contract as a cheap AST
check:
  1. every `skynetra.*` import inside the interface package resolves to
     a lower layer (foundation/domain/engines/orchestration) or to the
     interface package itself;
  2. the interface package collectively imports from ALL four lower
     layers (it must compose everything);
  3. no lower-layer module imports `skynetra.interface`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SKYNETRA_ROOT = Path(__file__).resolve().parent.parent.parent / "skynetra"
INTERFACE_DIR = SKYNETRA_ROOT / "interface"

LOWER_LAYERS = {"foundation", "domain", "engines", "orchestration"}
ALLOWED_TARGETS = LOWER_LAYERS | {"interface"}


def _iter_py_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


def _skynetra_imports(py_file: Path) -> list[tuple[str, int]]:
    tree = ast.parse(py_file.read_text(), filename=str(py_file))
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "skynetra" or alias.name.startswith("skynetra."):
                    top = alias.name.split(".")[1]
                    found.append((top, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "skynetra" or node.module.startswith("skynetra."):
                top = node.module.split(".")[1]
                found.append((top, node.lineno))
    return found


def test_interface_imports_only_lower_layers() -> None:
    errors: list[str] = []
    imported: set[str] = set()
    for py_file in _iter_py_files(INTERFACE_DIR):
        for top, lineno in _skynetra_imports(py_file):
            if top not in ALLOWED_TARGETS:
                errors.append(
                    f"{py_file.relative_to(SKYNETRA_ROOT)}:{lineno} "
                    f"imports skynetra.{top} (not a lower layer)"
                )
            elif top in LOWER_LAYERS:
                imported.add(top)
    assert not errors, "\n".join(errors)


def test_interface_imports_all_four_layers() -> None:
    imported: set[str] = set()
    for py_file in _iter_py_files(INTERFACE_DIR):
        for top, _lineno in _skynetra_imports(py_file):
            if top in LOWER_LAYERS:
                imported.add(top)
    assert imported == LOWER_LAYERS, f"interface imports: {sorted(imported)}"


def test_lower_layers_never_import_interface() -> None:
    errors: list[str] = []
    for py_file in _iter_py_files(SKYNETRA_ROOT):
        if INTERFACE_DIR in py_file.parents:
            continue
        for top, lineno in _skynetra_imports(py_file):
            if top == "interface":
                errors.append(
                    f"{py_file.relative_to(SKYNETRA_ROOT)}:{lineno} "
                    f"imports skynetra.interface from a lower layer"
                )
    assert not errors, "\n".join(errors)


@pytest.mark.parametrize(
    "module",
    ["skynetra.interface", "skynetra.interface.config.defaults", "skynetra.interface.cli"],
)
def test_interface_modules_import_cleanly(module: str) -> None:
    import importlib

    importlib.import_module(module)
