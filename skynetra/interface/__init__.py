"""
Interface layer (L4) — config, CLI, visualization, reporting.

May import from: any layer below (L0-L3). This is the only layer
permitted to see all of L0-L3 simultaneously and translate user intent
into concrete objects.
"""

from skynetra.interface.cli import main
from skynetra.interface.config.defaults import (
    config_to_simulation_spec,
    get_minimal_config,
    get_physics_enabled_config,
    load_config,
    save_config,
)
from skynetra.interface.config.schema import FullConfig
from skynetra.interface.reporting import compare_runs, export_results

__all__ = [
    "FullConfig",
    "load_config",
    "save_config",
    "get_physics_enabled_config",
    "get_minimal_config",
    "config_to_simulation_spec",
    "main",
    "export_results",
    "compare_runs",
]
