from __future__ import annotations

import ast
from pathlib import Path

import pytest

FOUNDATION_DIR = Path(__file__).resolve().parents[2] / "skynetra" / "foundation"

FORBIDDEN_LAYERS = {
    "skynetra.domain",
    "skynetra.engines",
    "skynetra.orchestration",
    "skynetra.interface",
}


def _module_paths() -> list[Path]:
    return sorted(FOUNDATION_DIR.rglob("*.py"))


def _import_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                modules.append(node.module)
    return modules


@pytest.mark.parametrize("py_file", _module_paths(), ids=lambda p: p.name)
def test_layer0_has_no_internal_imports(py_file: Path):
    assert _module_paths(), "foundation directory must contain module files"
    for module in _import_modules(py_file):
        for forbidden in FORBIDDEN_LAYERS:
            assert not (
                module == forbidden or module.startswith(forbidden + ".")
            ), (
                f"{py_file.name} imports '{module}', which violates "
                f"the L0 no-upward-import rule"
            )
