from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner

from skynetra.interface.cli import skynetra_cli


class TestCli:
    def setup_method(self):
        self.runner = CliRunner()

    def test_cli_help(self):
        result = self.runner.invoke(skynetra_cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_run_default(self):
        result = self.runner.invoke(skynetra_cli, ["run"])
        assert result.exit_code == 0
        assert "Running simulation for 3600.0s" in result.output

    def test_run_with_duration(self):
        result = self.runner.invoke(skynetra_cli, ["run", "--duration", "100.0"])
        assert result.exit_code == 0
        assert "Running simulation for 100.0s" in result.output

    def test_run_with_short_d(self):
        result = self.runner.invoke(skynetra_cli, ["run", "-d", "50.0"])
        assert result.exit_code == 0
        assert "Running simulation for 50.0s" in result.output

    def test_validate_valid_yaml(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump({"foundation": {"log_level": "INFO"}}, f)
            config_path = f.name
        try:
            result = self.runner.invoke(skynetra_cli, ["validate", config_path])
            assert result.exit_code == 0
            assert "Config is valid" in result.output
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_validate_nonexistent_path(self):
        result = self.runner.invoke(skynetra_cli, ["validate", "/nonexistent/config.yaml"])
        assert result.exit_code != 0

    def test_list_strategies(self):
        result = self.runner.invoke(skynetra_cli, ["list-strategies"])
        assert result.exit_code == 0
        assert "shortest_path" in result.output
        assert "backpressure" in result.output
        assert "thermal" in result.output
        assert "ai_training" in result.output

    def test_list_strategies_with_output(self):
        result = self.runner.invoke(skynetra_cli, ["list-strategies", "--output", "./custom"])
        assert result.exit_code == 0

    def test_cli_with_config_option(self):
        result = self.runner.invoke(skynetra_cli, ["--config", "config.yaml", "run"])
        assert result.exit_code == 0

    def test_cli_with_log_level(self):
        result = self.runner.invoke(skynetra_cli, ["--log-level", "DEBUG", "run"])
        assert result.exit_code == 0

    def test_run_subcommand_help(self):
        result = self.runner.invoke(skynetra_cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--duration" in result.output
