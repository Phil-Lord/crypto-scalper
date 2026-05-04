from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from scripts.run_backtest import run_backtest


@pytest.mark.scripts
@pytest.mark.run_backtest
class TestRunBacktest:

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_help_lists_no_optimise_flag(self, runner: CliRunner):
        result = runner.invoke(run_backtest, ['--help'])
        assert result.exit_code == 0
        assert '--optimise' not in result.output
        assert '-o,' not in result.output

    def test_fails_when_required_options_missing(self, runner: CliRunner):
        result = runner.invoke(run_backtest, [])
        assert result.exit_code != 0

    @patch('scripts.run_backtest.PLOT_RESULTS', False)
    @patch('scripts.run_backtest.create_engine')
    def test_runs_engine_once_without_optimise(self, mock_create_engine, runner: CliRunner):
        # Given
        engine = MagicMock()
        engine.run.return_value = MagicMock()
        engine.get_final_quote_balance.return_value = 1234.5
        mock_create_engine.return_value = engine

        # When
        result = runner.invoke(run_backtest, [
            '-p', 'BTC', '-sn', 'SmaStrategy', '-s', '2025-1-1-0-0-0', '-e', '2025-1-2-0-0-0',
        ])

        # Then
        assert result.exit_code == 0
        engine.run.assert_called_once()
        engine.optimise_parameters.assert_not_called()
