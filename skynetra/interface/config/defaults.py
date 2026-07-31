"""
Interface layer (L4) — config load/save and presets.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from skynetra.interface.config.schema import FullConfig

PRESETS: Dict[str, Dict[str, Any]] = {
    "small": {
        "domain": {
            "constellation": {
                "num_planes": 2,
                "satellites_per_plane": 4,
            }
        },
        "orchestration": {"duration": 600.0, "dt": 5.0},
    },
    "medium": {
        "domain": {
            "constellation": {
                "num_planes": 6,
                "satellites_per_plane": 11,
            }
        },
        "orchestration": {"duration": 3600.0, "dt": 1.0},
    },
    "large": {
        "domain": {
            "constellation": {
                "num_planes": 12,
                "satellites_per_plane": 22,
            }
        },
        "orchestration": {"duration": 14400.0, "dt": 0.5},
    },
}


def load_config(path: str) -> FullConfig:
    p = Path(path)
    raw: Dict[str, Any] = {}
    if p.suffix in (".yaml", ".yml"):
        with open(p) as f:
            raw = yaml.safe_load(f) or {}
    elif p.suffix == ".json":
        with open(p) as f:
            raw = json.load(f)
    else:
        raise ValueError(f"Unsupported config format: {p.suffix}")
    preset_name = raw.pop("preset", None)
    if preset_name:
        preset = PRESETS.get(preset_name)
        if preset:
            raw = _deep_merge(preset, raw)
    return FullConfig(**raw)


def save_config(config: FullConfig, path: str) -> None:
    p = Path(path)
    raw = config.model_dump(mode="json")
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix in (".yaml", ".yml"):
        with open(p, "w") as f:
            yaml.dump(raw, f, default_flow_style=False)
    elif p.suffix == ".json":
        with open(p, "w") as f:
            json.dump(raw, f, indent=2)
    else:
        raise ValueError(f"Unsupported config format: {p.suffix}")


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    result = base.copy()
    for key, val in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result
