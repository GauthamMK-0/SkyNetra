"""
Interface layer (L4) — FullConfig Pydantic v2 schema.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FoundationConfig(BaseModel):
    log_level: str = "INFO"
    use_structlog: bool = False


class ConstellationSection(BaseModel):
    name: str = "default"
    num_planes: int = 6
    satellites_per_plane: int = 11
    inclination: float = 53.0
    altitude_km: float = 550.0
    eccentricity: float = 0.0


class DomainConfig(BaseModel):
    constellation: ConstellationSection = Field(default_factory=ConstellationSection)
    isl_threshold: float = 0.01
    earth_radius_km: float = 6371.0


class RoutingSection(BaseModel):
    strategy: str = "shortest_path"
    params: Dict[str, Any] = Field(default_factory=dict)


class PhysicsSection(BaseModel):
    models: List[str] = Field(default_factory=lambda: ["thermal", "radiation", "power"])
    params: Dict[str, Any] = Field(default_factory=dict)


class WorkloadSection(BaseModel):
    generators: List[str] = Field(default_factory=lambda: ["ai_training"])
    params: Dict[str, Any] = Field(default_factory=dict)


class EnginesConfig(BaseModel):
    routing: RoutingSection = Field(default_factory=RoutingSection)
    physics: PhysicsSection = Field(default_factory=PhysicsSection)
    workload: WorkloadSection = Field(default_factory=WorkloadSection)


class MetricsSection(BaseModel):
    collectors: List[str] = Field(
        default_factory=lambda: ["network", "compute", "topology", "physics"]
    )


class OrchestrationConfig(BaseModel):
    duration: float = 3600.0
    dt: float = 1.0
    metrics: MetricsSection = Field(default_factory=MetricsSection)


class VizConfig(BaseModel):
    enabled: bool = True
    output_dir: str = "./output"
    dpi: int = 150


class InterfaceConfig(BaseModel):
    viz: VizConfig = Field(default_factory=VizConfig)


class FullConfig(BaseModel):
    foundation: FoundationConfig = Field(default_factory=FoundationConfig)
    domain: DomainConfig = Field(default_factory=DomainConfig)
    engines: EnginesConfig = Field(default_factory=EnginesConfig)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    interface: InterfaceConfig = Field(default_factory=InterfaceConfig)
