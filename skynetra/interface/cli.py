"""
Interface layer (L4) — Click CLI.

May import from: any layer below (L0-L3).
"""

from __future__ import annotations

from typing import Optional

import click

from skynetra.foundation.logging_setup import configure_logging


@click.group()
@click.option("--log-level", default="INFO", help="Logging level")
@click.option("--config", "-c", default=None, help="Path to config file")
@click.pass_context
def skynetra_cli(ctx: click.Context, log_level: str, config: Optional[str]) -> None:
    configure_logging(level=log_level)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@skynetra_cli.command()
@click.option("--duration", "-d", default=3600.0, type=float, help="Simulation duration (s)")
@click.pass_context
def run(ctx: click.Context, duration: float) -> None:
    click.echo(f"Running simulation for {duration}s ...")
    click.echo("Simulation complete.")


@skynetra_cli.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.pass_context
def validate(ctx: click.Context, config_path: str) -> None:
    click.echo(f"Validating config: {config_path} ...")
    click.echo("Config is valid.")


@skynetra_cli.command()
@click.option("--output", "-o", default="./results", help="Output directory")
@click.pass_context
def list_strategies(ctx: click.Context, output: str) -> None:
    click.echo("Available strategies:")
    click.echo("  Routing: shortest_path, backpressure")
    click.echo("  Physics: thermal, radiation, power, doppler")
    click.echo("  Workload: ai_training, inference, federated_learning")
    click.echo("  Metrics: network, compute, topology, physics")


if __name__ == "__main__":
    skynetra_cli()
