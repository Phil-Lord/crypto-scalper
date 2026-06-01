import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from core import JsonTrialProgressCallback
from scripts.optimise_in_sample import optimise_in_sample
from utils import get_second_timestamp, parse_datetime


@pytest.mark.scripts
@pytest.mark.optimise_in_sample
class TestOptimiseInSampleCli:

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_help_smoke(self, runner: CliRunner):
        result = runner.invoke(optimise_in_sample, ['--help'])
        assert result.exit_code == 0
        assert '--pair' in result.output
        assert '--strategy_name' in result.output
        assert '--n_trials' in result.output
        assert '--n_workers' in result.output

    def test_fails_when_required_options_missing(self, runner: CliRunner):
        result = runner.invoke(optimise_in_sample, [])
        assert result.exit_code != 0

    @patch('scripts.optimise_in_sample.run_in_sample_optimisation')
    def test_emits_done_with_trial_count_on_stdout(
        self, mock_run, runner: CliRunner
    ):
        # When
        result = runner.invoke(optimise_in_sample, [
            '-p', 'BTC', '-sn', 'SmaStrategy',
            '-s', '2025-1-1-0-0-0', '-e', '2025-4-1-0-0-0',
            '-n', '7',
        ])

        # Then
        assert result.exit_code == 0, result.output
        last_line = result.output.strip().splitlines()[-1]
        event, payload_json = last_line.split(' ', 1)
        assert event == 'DONE'
        assert json.loads(payload_json) == {'trials': 7}

    @patch('scripts.optimise_in_sample.run_in_sample_optimisation')
    def test_parses_datetime_args_into_unix_timestamps(
        self, mock_run, runner: CliRunner
    ):
        # When
        result = runner.invoke(optimise_in_sample, [
            '-p', 'BTC', '-sn', 'SmaStrategy',
            '-s', '2025-1-1-0-0-0', '-e', '2025-4-1-0-0-0',
            '-n', '5',
        ])

        # Then
        assert result.exit_code == 0, result.output
        kwargs = mock_run.call_args.kwargs
        assert kwargs['start'] == get_second_timestamp(*parse_datetime('2025-1-1-0-0-0'))
        assert kwargs['end'] == get_second_timestamp(*parse_datetime('2025-4-1-0-0-0'))

    @patch('scripts.optimise_in_sample.run_in_sample_optimisation')
    def test_passes_typed_kwargs_and_callback_to_run(
        self, mock_run, runner: CliRunner
    ):
        # When — default -w 1 runs in-process.
        result = runner.invoke(optimise_in_sample, [
            '-p', 'BTC', '-sn', 'SmaStrategy',
            '-s', '2025-1-1-0-0-0', '-e', '2025-4-1-0-0-0',
            '-n', '5',
        ])

        # Then
        assert result.exit_code == 0, result.output
        kwargs = mock_run.call_args.kwargs
        assert kwargs['pair'] == 'BTC'
        assert kwargs['strategy_name'] == 'SmaStrategy'
        assert kwargs['n_trials'] == 5
        assert isinstance(kwargs['progress_callback'], JsonTrialProgressCallback)

    @patch('scripts.optimise_in_sample.run_in_sample_workers')
    @patch('scripts.optimise_in_sample.run_in_sample_optimisation')
    def test_single_worker_runs_in_process_not_via_subprocess_fanout(
        self, mock_run, mock_workers, runner: CliRunner
    ):
        # When
        result = runner.invoke(optimise_in_sample, [
            '-p', 'BTC', '-sn', 'SmaStrategy',
            '-s', '2025-1-1-0-0-0', '-e', '2025-4-1-0-0-0',
            '-n', '5', '-w', '1',
        ])

        # Then — in-process path used, fan-out untouched.
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        mock_workers.assert_not_called()

    @patch('scripts.optimise_in_sample.run_in_sample_workers')
    @patch('scripts.optimise_in_sample.run_in_sample_optimisation')
    def test_multiple_workers_fans_out_to_subprocess_helper(
        self, mock_run, mock_workers, runner: CliRunner
    ):
        # When
        result = runner.invoke(optimise_in_sample, [
            '-p', 'BTC', '-sn', 'SmaStrategy',
            '-s', '2025-1-1-0-0-0', '-e', '2025-4-1-0-0-0',
            '-n', '10', '-w', '3',
        ])

        # Then — fan-out helper used with typed args, in-process path untouched.
        assert result.exit_code == 0, result.output
        mock_run.assert_not_called()
        kwargs = mock_workers.call_args.kwargs
        assert kwargs['pair'] == 'BTC'
        assert kwargs['strategy_name'] == 'SmaStrategy'
        assert kwargs['n_trials'] == 10
        assert kwargs['n_workers'] == 3
