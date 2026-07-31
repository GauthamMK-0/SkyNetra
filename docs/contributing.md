# Contributing

Internal development guidelines for the SkyNetra team.

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, release-ready code. Protected — requires PR + review. |
| `develop` | Integration branch for feature work. |
| `feat/*` | Feature branches branched from `develop`. |
| `fix/*` | Bug-fix branches branched from `develop` or `main` for hotfixes. |
| `docs/*` | Documentation-only changes. |

## PR Process

1. Create a feature/fix branch from `develop`
2. Make changes, keeping commits small and logical
3. Run all tests locally: `pytest`
4. Run layer boundary checks: `import-linter .` and `pytest tests/layer_boundaries/`
5. Run linting: `ruff check .`
6. Run type checking: `mypy skynetra`
7. Open a pull request against `develop`
8. Ensure CI passes (all matrix Python versions)
9. Request review from at least one team member
10. Squash-merge into `develop` after approval

Hotfixes to `main` follow the same process but branch from `main` and merge back to both `main` and `develop`.

## Testing Requirements

- All new code must have tests
- Tests live in `tests/` mirroring the `skynetra/` package structure
- Test files follow the pattern `test_<module>.py`
- Use pytest idioms: fixtures, parametrize, conftest
- Aim for at least 80% coverage on new code
- Run: `pytest --cov=skynetra`

Existing test directory structure:

| Directory | What It Tests |
|-----------|---------------|
| `tests/layer0/` | Foundation layer |
| `tests/layer1/` | Domain layer |
| `tests/layer2/` | Engine strategies |
| `tests/layer4/` | Interface layer |
| `tests/layer_boundaries/` | Import dependency enforcement |
| `tests/integration/` | End-to-end simulations |

## Layer Boundary Enforcement

Every PR must pass both checks:

```bash
import-linter .
pytest tests/layer_boundaries/
```

The `.importlinter` config defines the layer ordering. The AST-based test scans all `.py` files for upward imports. Both must pass.

## Coding Standards

### Style

- **Line length:** 100 characters
- **Formatter:** Black (`target-version = py311`)
- **Linter:** Ruff (select: E, F, I, W)
- **Type checker:** mypy (`strict = true`)
- **Python version:** 3.11 minimum

### Conventions

- Use `from __future__ import annotations` in every file
- Use type annotations on all function signatures
- Dataclasses preferred over plain classes for data holders
- ABCs for all pluggable interfaces
- Module-level `STRATEGIES` dict for registration (side-effect pattern)
- `__init__.py` exports define public API; everything else is private
- Docstrings on modules should state layer dependency rules:

```python
"""
Layer label — brief description.

May import from: itself, [lower layers].
"""
```

### Imports

- Standard library first, then third-party, then `skynetra`
- Prefer explicit imports over star imports
- Never import from a higher layer

## Commit Messages

Follow conventional commits:

```
<type>(<scope>): <short description>

feat:     new feature
fix:      bug fix
docs:     documentation
refactor: code restructuring
test:     adding/modifying tests
chore:    build/config/tooling
```

Example: `feat(physics): add MagnetosphereModel for radiation belt effects`
