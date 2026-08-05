"""Layer 4 config tests: FullConfig schema, load/save, translation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from skynetra.interface.config.defaults import (
    config_to_simulation_spec,
    get_minimal_config,
    get_physics_enabled_config,
    load_config,
    save_config,
)
from skynetra.interface.config.schema import FullConfig
from skynetra.orchestration.engine import OrbitDCSimulation


class TestFullConfigSchema:
    def test_defaults(self) -> None:
        cfg = FullConfig()
        assert cfg.routing.strategy == "shortest_path"
        assert cfg.simulation.duration_s == 60.0
        assert cfg.simulation.seed == 42
        assert cfg.constellation.n_planes == 3
        assert cfg.constellation.sats_per_plane == 6
        assert cfg.pods.n_pods == 1
        assert cfg.ground_stations.n_ground_stations == 1
        assert cfg.workload.active == ["ai_training_sync", "inference_query"]
        assert cfg.metrics.active == [
            "network_metrics",
            "compute_metrics",
            "topology_metrics",
        ]
        for section in (
            cfg.physics.thermal,
            cfg.physics.radiation,
            cfg.physics.power,
            cfg.physics.doppler,
        ):
            assert section["enabled"] is False

    def test_extra_forbid(self) -> None:
        with pytest.raises(ValidationError):
            FullConfig(unknown_section={"foo": 1})

    def test_invalid_routing_strategy(self) -> None:
        with pytest.raises(ValidationError):
            FullConfig(routing={"strategy": "quantum_wormhole"})

    def test_physics_enabled_preset(self) -> None:
        cfg = get_physics_enabled_config()
        assert cfg.physics.thermal["enabled"] is True
        assert cfg.physics.radiation["enabled"] is True
        assert cfg.physics.power["enabled"] is True
        assert cfg.physics.doppler["enabled"] is False

    def test_minimal_config(self) -> None:
        cfg = get_minimal_config()
        assert cfg.simulation.duration_s == 60.0
        assert cfg.simulation.seed == 42
        assert cfg.constellation.n_planes == 2
        assert cfg.constellation.sats_per_plane == 3
        assert cfg.pods.n_pods == 1


class TestLoadSave:
    def test_roundtrip_yaml(self, tmp_path: Path) -> None:
        path = str(tmp_path / "cfg.yaml")
        save_config(get_physics_enabled_config(), path)
        loaded = load_config(path)
        assert loaded == get_physics_enabled_config()

    def test_roundtrip_json(self, tmp_path: Path) -> None:
        path = str(tmp_path / "cfg.json")
        save_config(FullConfig(), path)
        loaded = load_config(path)
        assert loaded == FullConfig()

    def test_loads_hand_written_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "cfg.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "simulation": {"duration_s": 120.0},
                    "routing": {"strategy": "backpressure"},
                }
            )
        )
        cfg = load_config(str(path))
        assert cfg.simulation.duration_s == 120.0
        assert cfg.routing.strategy == "backpressure"
        assert cfg.pods.n_pods == 1

    def test_unsupported_format(self, tmp_path: Path) -> None:
        path = str(tmp_path / "cfg.toml")
        with pytest.raises(ValueError):
            load_config(path)

    def test_saved_file_is_plain_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "cfg.yaml"
        save_config(FullConfig(), str(path))
        raw = yaml.safe_load(path.read_text())
        assert raw["simulation"]["duration_s"] == 60.0
        assert raw["physics"]["thermal"]["enabled"] is False


class TestConfigToSimulationSpec:
    def test_default_config_spec(self) -> None:
        spec = config_to_simulation_spec(FullConfig())
        assert isinstance(spec, OrbitDCSimulation.SimulationSpec)
        assert spec.constellation.total_satellites == 18
        assert spec.n_pods == 1
        assert spec.n_ground_stations == 1
        assert spec.routing_strategy == "shortest_path"
        assert spec.routing_config == {}
        assert spec.physics_specs == []
        assert [w["name"] for w in spec.workload_specs] == [
            "ai_training_sync",
            "inference_query",
        ]
        assert [m["name"] for m in spec.metrics_specs] == [
            "network_metrics",
            "compute_metrics",
            "topology_metrics",
        ]
        assert spec.sim_duration_s == 60.0
        assert spec.topology_update_interval_s == 10.0
        assert spec.physics_tick_interval_s == 1.0
        assert spec.seed == 42

    def test_physics_enabled_spec(self) -> None:
        cfg = get_physics_enabled_config()
        spec = config_to_simulation_spec(cfg)
        assert [p["name"] for p in spec.physics_specs] == ["thermal", "radiation", "power"]
        for entry in spec.physics_specs:
            assert entry["config"]["enabled"] is True

    def test_custom_sections_flow_through(self) -> None:
        cfg = FullConfig(
            routing={"strategy": "backpressure", "config": {"q_scale": 2.0}},
            workload={
                "active": ["federated_learning"],
                "federated_learning": {"sync_interval_s": 5.0},
            },
            metrics={"active": ["physics_metrics"]},
            simulation={"duration_s": 30.0, "seed": 7},
            constellation={"n_planes": 4, "sats_per_plane": 5},
        )
        spec = config_to_simulation_spec(cfg)
        assert spec.routing_strategy == "backpressure"
        assert spec.routing_config == {"q_scale": 2.0}
        assert spec.workload_specs == [
            {"name": "federated_learning", "config": {"sync_interval_s": 5.0}}
        ]
        assert spec.metrics_specs == [{"name": "physics_metrics"}]
        assert spec.sim_duration_s == 30.0
        assert spec.seed == 7
        assert spec.constellation.total_satellites == 20

    def test_spec_is_consumable_by_engine(self) -> None:
        spec = config_to_simulation_spec(get_minimal_config())
        results = OrbitDCSimulation.from_spec(spec).run()
        assert results.duration == 60.0
        net = results.engine_metrics["network_metrics"]
        assert net["delivered"] >= 0
