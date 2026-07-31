"""
Interface layer (L4) — export and comparison utilities.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml


def export_results(results: Dict[str, Any], path: str, fmt: str = "json") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        with open(p, "w") as f:
            json.dump(results, f, indent=2, default=str)
    elif fmt == "yaml":
        with open(p, "w") as f:
            yaml.dump(results, f, default_flow_style=False)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def compare_runs(runs: List[Dict[str, Any]], keys: List[str]) -> Dict[str, Any]:
    comparison: Dict[str, Any] = {}
    for key in keys:
        comparison[key] = [run.get(key) for run in runs]
    return comparison
