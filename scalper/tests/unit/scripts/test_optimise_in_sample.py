import json
import sys
from unittest.mock import MagicMock, patch

import optuna
import pytest
from click.testing import CliRunner

from scripts.optimise_in_sample import JsonProgressCallback, build_command, optimise_in_sample


@pytest.mark.scripts
@pytest.mark.optimise_in_sample
class TestBuildCommand:
    def test_includes_all_required_flags(self):
        cmd = build_command(
            'BTCGBP', 'PrecisionTrendStrategy', '2025-1-1-0-0-0', '2025-4-1-0-0-0',
            n_trials=50,
        )

        assert cmd[0] == sys.executable
        assert cmd[1:3] == ['-m', 'scripts.optimise_in_sample']
        assert cmd[cmd.index('-p') + 1] == 'BTCGBP'
        assert cmd[cmd.index('-sn') + 1] == 'PrecisionTrendStrategy'
        assert cmd[cmd.index('-s') + 1] == '2025-1-1-0-0-0'
        assert cmd[cmd.index('-e') + 1] == '2025-4-1-0-0-0'
        assert cmd[cmd.index('-n') + 1] == '50'
        assert cmd[cmd.index('-j') + 1] == '1'

    def test_overrides_n_jobs(self):
        cmd = build_command('BTCGBP', 'SmaStrategy', 's', 'e', n_trials=10, n_jobs=4)
        assert cmd[cmd.index('-j') + 1] == '4'


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

    @patch('scripts.optimise_in_sample.build_engine')
    def test_emits_done_with_trial_count_on_stdout(
        self, mock_build_engine, runner: CliRunner
    ):
        # Given
        engine = MagicMock()
        mock_build_engine.return_value = engine

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

    @patch('scripts.optimise_in_sample.build_engine')
    def test_passes_callback_and_n_jobs_to_engine(
        self, mock_build_engine, runner: CliRunner
    ):
        # Given
        engine = MagicMock()
        mock_build_engine.return_value = engine

        # When
        result = runner.invoke(optimise_in_sample, [
            '-p', 'BTC', '-sn', 'SmaStrategy',
            '-s', '2025-1-1-0-0-0', '-e', '2025-4-1-0-0-0',
            '-n', '5', '-j', '2',
        ])

        # Then
        assert result.exit_code == 0, result.output
        kwargs = engine.optimise_parameters.call_args.kwargs
        assert kwargs['n_trials'] == 5
        assert kwargs['n_jobs'] == 2
        assert isinstance(kwargs['progress_callback'], JsonProgressCallback)


@pytest.mark.scripts
@pytest.mark.optimise_in_sample
class TestJsonProgressCallback:

    def test_emits_progress_line_per_trial(self, capsys):
        # Given
        callback = JsonProgressCallback()
        study = MagicMock()
        study.best_value = 1.45
        completed_trial = MagicMock()
        completed_trial.state = optuna.trial.TrialState.COMPLETE
        study.get_trials.return_value = [completed_trial]
        trial = MagicMock()
        trial.number = 42
        trial.value = 1.234

        # When
        callback(study, trial)

        # Then
        out = capsys.readouterr().out.strip()
        event, payload_json = out.split(' ', 1)
        assert event == 'PROGRESS'
        assert json.loads(payload_json) == {'trial': 42, 'value': 1.234, 'best': 1.45}

    def test_best_is_none_when_no_completed_trials(self, capsys):
        # Given
        callback = JsonProgressCallback()
        study = MagicMock()
        study.get_trials.return_value = []
        trial = MagicMock()
        trial.number = 0
        trial.value = None

        # When
        callback(study, trial)

        # Then
        out = capsys.readouterr().out.strip()
        _, payload_json = out.split(' ', 1)
        assert json.loads(payload_json) == {'trial': 0, 'value': None, 'best': None}
