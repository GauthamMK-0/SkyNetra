"""
Interface layer (L4) — config subpackage.

May import from: any layer below (L0-L3).
"""

from skynetra.interface.config.defaults import PRESETS, load_config, save_config
from skynetra.interface.config.schema import FullConfig

__all__ = [
    "FullConfig",
    "load_config",
    "save_config",
    "PRESETS",
]
