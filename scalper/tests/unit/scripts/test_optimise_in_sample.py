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
        assert '--n_jobs' in result.output

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
        # When
        result = runner.invoke(optimise_in_sample, [
            '-p', 'BTC', '-sn', 'SmaStrategy',
            '-s', '2025-1-1-0-0-0', '-e', '2025-4-1-0-0-0',
            '-n', '5', '-j', '2',
        ])

        # Then
        assert result.exit_code == 0, result.output
        kwargs = mock_run.call_args.kwargs
        assert kwargs['pair'] == 'BTC'
        assert kwargs['strategy_name'] == 'SmaStrategy'
        assert kwargs['n_trials'] == 5
        assert kwargs['n_jobs'] == 2
        assert isinstance(kwargs['progress_callback'], JsonTrialProgressCallback)
