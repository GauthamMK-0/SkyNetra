"""AST-based import boundary check for the Layer 2 physics subpackage.

Layer 2 (`skynetra.engines`) may import ONLY from itself and lower layers
(L0 `skynetra.foundation`, L1 `skynetra.domain`). The physics subpackage
must never import from Layer 3 (`skynetra.orchestration`) or Layer 4
(`skynetra.interface`). This is a static AST scan of every `.py` file
under `skynetra/engines/physics/`.

The legacy project name was `skynetra` with layers
`skynetra.layer2_engines` / `skynetra.layer3_*` / `skynetra.layer4_*`; any
reference to those strings is flagged as well.
"""

from __future__ import annotations

import ast
from pathlib import Path

PHYSICS_ROOT = Path(__file__).resolve().parent.parent.parent / "skynetra" / "engines" / "physics"

FORBIDDEN_TOP_LEVEL_MODULES = {
    "orchestration",  # skynetra.orchestration — Layer 3
    "interface",  # skynetra.interface — Layer 4
}

FORBIDDEN_STRINGS = (
    "skynetra.layer3",
    "skynetra.layer4",
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


def test_layer2_physics_files_exist() -> None:
    assert PHYSICS_ROOT.is_dir()
    assert list(PHYSICS_ROOT.rglob("*.py")), "skynetra/engines/physics must contain modules"


def test_layer2_physics_has_no_upward_imports() -> None:
    violations: list[str] = []
    for py_file in sorted(PHYSICS_ROOT.rglob("*.py")):
        for module, lineno in _extract_imports(py_file):
            if module.split(".")[0] in FORBIDDEN_TOP_LEVEL_MODULES:
                violations.append(
                    f"{py_file.relative_to(PHYSICS_ROOT.parent.parent.parent)}:{lineno} "
                    f"imports forbidden module '{module}'"
                )
    assert not violations, "\n".join(violations)


def test_layer2_physics_has_no_legacy_skynetra_layer_references() -> None:
    violations: list[str] = []
    for py_file in sorted(PHYSICS_ROOT.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            if any(token in line for token in FORBIDDEN_STRINGS):
                violations.append(
                    f"{py_file.relative_to(PHYSICS_ROOT.parent.parent.parent)}:{line_no}: {line}"
                )
    assert not violations, "\n".join(violations)
