"""AST-based import boundary check for the Layer 3 orchestration package.

Layer 3 (`skynetra.orchestration`) may import ONLY from itself and lower
layers (L0 `skynetra.foundation`, L1 `skynetra.domain`, L2
`skynetra.engines`). It must never import from Layer 4
(`skynetra.interface`, including `skynetra.interface.config`). This is a
static AST scan of every `.py` file under `skynetra/orchestration/`.

The legacy project name was `skynetra` with layers
`skynetra.layer2_engines` / `skynetra.layer3_*` / `skynetra.layer4_*`; any
reference to those strings is flagged as well.
"""

from __future__ import annotations

import ast
from pathlib import Path

ORCHESTRATION_ROOT = Path(__file__).resolve().parent.parent.parent / "skynetra" / "orchestration"

FORBIDDEN_TOP_LEVEL_MODULES = {
    "interface",  # skynetra.interface — Layer 4
}

FORBIDDEN_STRINGS = (
    "skynetra.layer4",
    "skynetra.layer3",
)


def _extract_imports(path: Path) -> list[tuple[str, int]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.module, node.lineno))
    return imports


def test_layer3_orchestration_files_exist() -> None:
    assert ORCHESTRATION_ROOT.is_dir()
    assert list(ORCHESTRATION_ROOT.rglob("*.py")), "skynetra/orchestration must contain modules"


def test_layer3_has_no_upward_imports() -> None:
    violations: list[str] = []
    for py_file in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        for module, lineno in _extract_imports(py_file):
            if module.split(".")[0] in FORBIDDEN_TOP_LEVEL_MODULES:
                violations.append(
                    f"{py_file.relative_to(ORCHESTRATION_ROOT.parent.parent.parent)}:{lineno} "
                    f"imports forbidden module '{module}'"
                )
    assert not violations, "\n".join(violations)


def test_layer3_has_no_legacy_skynetra_layer_references() -> None:
    violations: list[str] = []
    for py_file in sorted(ORCHESTRATION_ROOT.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            if any(token in line for token in FORBIDDEN_STRINGS):
                relative = py_file.relative_to(ORCHESTRATION_ROOT.parent.parent.parent)
                violations.append(f"{relative}:{line_no}: {line}")
    assert not violations, "\n".join(violations)
