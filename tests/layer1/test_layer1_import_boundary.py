"""AST-based import boundary check for the Layer 1 domain package.

Layer 1 may import ONLY from itself and the foundation layer (L0).
It must never import from Layer 2 (`skynetra.engines`), Layer 3
(`skynetra.orchestration`), or Layer 4 (`skynetra.interface`). This is a
static AST scan of every `.py` file under `skynetra/domain/` — the same
mechanical guarantee the project-wide boundary tests provide, but scoped
to the L1 package so a Layer 1 regression cannot hide behind the upper
layers' own failures.

The legacy project name was `skynetra` with layers
`skynetra.layer2_engines` / `skynetra.layer3_*` / `skynetra.layer4_*`; any
reference to those strings is flagged as well.
"""

from __future__ import annotations

import ast
from pathlib import Path

DOMAIN_ROOT = Path(__file__).resolve().parent.parent.parent / "skynetra" / "domain"

FORBIDDEN_TOP_LEVEL_MODULES = {
    "engines",  # skynetra.engines — Layer 2
    "orchestration",  # skynetra.orchestration — Layer 3
    "interface",  # skynetra.interface — Layer 4
}

FORBIDDEN_STRINGS = (
    "skynetra.layer2",
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


def test_layer1_domain_files_exist() -> None:
    assert DOMAIN_ROOT.is_dir()
    assert list(DOMAIN_ROOT.rglob("*.py")), "skynetra/domain must contain modules"


def test_layer1_has_no_upward_imports() -> None:
    violations: list[str] = []
    for py_file in sorted(DOMAIN_ROOT.rglob("*.py")):
        for module, lineno in _extract_imports(py_file):
            if module.split(".")[0] in FORBIDDEN_TOP_LEVEL_MODULES:
                violations.append(
                    f"{py_file.relative_to(DOMAIN_ROOT.parent.parent)}:{lineno} "
                    f"imports forbidden module '{module}'"
                )
    assert not violations, "\n".join(violations)


def test_layer1_has_no_legacy_skynetra_layer_references() -> None:
    violations: list[str] = []
    for py_file in sorted(DOMAIN_ROOT.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), start=1):
            if any(token in line for token in FORBIDDEN_STRINGS):
                violations.append(
                    f"{py_file.relative_to(DOMAIN_ROOT.parent.parent)}:{line_no}: {line}"
                )
    assert not violations, "\n".join(violations)
