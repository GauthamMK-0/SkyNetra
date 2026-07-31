from __future__ import annotations

import json
import tempfile
from pathlib import Path

import yaml

from skynetra.interface.config.schema import (
    FullConfig,
    FoundationConfig,
    DomainConfig,
    ConstellationSection,
    EnginesConfig,
    RoutingSection,
    PhysicsSection,
    WorkloadSection,
    OrchestrationConfig,
    MetricsSection,
    InterfaceConfig,
    VizConfig,
)
from skynetra.interface.config.defaults import (
    load_config,
    save_config,
    PRESETS,
    _deep_merge,
)


class TestFullConfig:
    def test_default_construction(self):
        config = FullConfig()
        assert isinstance(config.foundation, FoundationConfig)
        assert isinstance(config.domain, DomainConfig)
        assert isinstance(config.engines, EnginesConfig)
        assert isinstance(config.orchestration, OrchestrationConfig)
        assert isinstance(config.interface, InterfaceConfig)

    def test_foundation_defaults(self):
        config = FullConfig()
        assert config.foundation.log_level == "INFO"
        assert config.foundation.use_structlog is False

    def test_domain_constellation_defaults(self):
        config = FullConfig()
        c = config.domain.constellation
        assert c.name == "default"
        assert c.num_planes == 6
        assert c.satellites_per_plane == 11
        assert c.inclination == 53.0
        assert c.altitude_km == 550.0

    def test_custom_routing(self):
        config = FullConfig(engines=EnginesConfig(routing=RoutingSection(strategy="backpressure")))
        assert config.engines.routing.strategy == "backpressure"

    def test_custom_physics(self):
        config = FullConfig(
            engines=EnginesConfig(
                physics=PhysicsSection(models=["thermal", "power"])
            )
        )
        assert config.engines.physics.models == ["thermal", "power"]

    def test_custom_workload(self):
        config = FullConfig(
            engines=EnginesConfig(
                workload=WorkloadSection(generators=["inference"])
            )
        )
        assert config.engines.workload.generators == ["inference"]

    def test_orchestration_defaults(self):
        config = FullConfig()
        assert config.orchestration.duration == 3600.0
        assert config.orchestration.dt == 1.0
        assert "network" in config.orchestration.metrics.collectors

    def test_interface_defaults(self):
        config = FullConfig()
        assert config.interface.viz.enabled is True
        assert config.interface.viz.output_dir == "./output"

    def test_model_dump_roundtrip(self):
        config = FullConfig()
        data = config.model_dump(mode="json")
        restored = FullConfig(**data)
        assert restored.model_dump(mode="json") == data


class TestConfigLoadSave:
    def test_save_and_load_yaml_roundtrip(self):
        config = FullConfig(
            foundation=FoundationConfig(log_level="DEBUG"),
            domain=DomainConfig(),
        )
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            path = f.name
            save_config(config, path)
        try:
            loaded = load_config(path)
            assert loaded.foundation.log_level == "DEBUG"
            assert loaded.model_dump(mode="json") == config.model_dump(mode="json")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_save_and_load_json_roundtrip(self):
        config = FullConfig()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            path = f.name
            save_config(config, path)
        try:
            loaded = load_config(path)
            assert loaded.model_dump(mode="json") == config.model_dump(mode="json")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_load_yaml_with_overrides(self):
        data = {
            "foundation": {"log_level": "ERROR"},
            "orchestration": {"duration": 100.0},
        }
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(data, f)
            path = f.name
        try:
            config = load_config(path)
            assert config.foundation.log_level == "ERROR"
            assert config.orchestration.duration == 100.0
        finally:
            Path(path).unlink(missing_ok=True)

    def test_load_json_with_overrides(self):
        data = {"foundation": {"log_level": "WARN"}, "domain": {"constellation": {"num_planes": 3}}}
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            config = load_config(path)
            assert config.foundation.log_level == "WARN"
            assert config.domain.constellation.num_planes == 3
        finally:
            Path(path).unlink(missing_ok=True)

    def test_unsupported_format_raises(self):
        with tempfile.NamedTemporaryFile(suffix=".toml", mode="w", delete=False) as f:
            path = f.name
        try:
            with open(path, "w") as f:
                f.write("key=value")
            import pytest
            with pytest.raises(ValueError, match="Unsupported config format"):
                load_config(path)
        finally:
            Path(path).unlink(missing_ok=True)


class TestPresets:
    def test_small_preset(self):
        preset = PRESETS["small"]
        assert preset["domain"]["constellation"]["num_planes"] == 2
        assert preset["orchestration"]["duration"] == 600.0

    def test_medium_preset(self):
        preset = PRESETS["medium"]
        assert preset["domain"]["constellation"]["num_planes"] == 6

    def test_large_preset(self):
        preset = PRESETS["large"]
        assert preset["domain"]["constellation"]["num_planes"] == 12
        assert preset["orchestration"]["duration"] == 14400.0

    def test_preset_used_in_load(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump({"preset": "small"}, f)
            path = f.name
        try:
            config = load_config(path)
            assert config.domain.constellation.num_planes == 2
            assert config.orchestration.duration == 600.0
        finally:
            Path(path).unlink(missing_ok=True)

    def test_preset_with_overrides(self):
        overrides = {"preset": "small", "orchestration": {"duration": 1234.0}}
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(overrides, f)
            path = f.name
        try:
            config = load_config(path)
            assert config.domain.constellation.num_planes == 2
            assert config.orchestration.duration == 1234.0
        finally:
            Path(path).unlink(missing_ok=True)


class TestDeepMerge:
    def test_basic_merge(self):
        base = {"a": 1, "b": {"c": 2}}
        override = {"b": {"d": 3}}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": {"c": 2, "d": 3}}

    def test_override_scalar(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3}

    def test_nested_override(self):
        base = {"x": {"y": {"z": 1}}}
        override = {"x": {"y": {"w": 2}}}
        result = _deep_merge(base, override)
        assert result == {"x": {"y": {"z": 1, "w": 2}}}

    def test_empty_override(self):
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == base
