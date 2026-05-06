import json
import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from scripts.evaluate_out_of_sample import (
    JsonProgressCallback,
    build_command,
    evaluate_out_of_sample,
)


@pytest.mark.scripts
@pytest.mark.evaluate_out_of_sample
class TestBuildCommand:
    def test_includes_all_required_flags(self):
        cmd = build_command(
            'PrecisionTrendStrategy_XXBTZGBP_20250101-20250401',
            num_sets=10,
            start='2025-4-1-0-0-0',
            end='2025-7-1-0-0-0',
            n_workers=2,
        )

        assert cmd[0] == sys.executable
        assert cmd[1:3] == ['-m', 'scripts.evaluate_out_of_sample']
        assert cmd[cmd.index('-sn') + 1] == 'PrecisionTrendStrategy_XXBTZGBP_20250101-20250401'
        assert cmd[cmd.index('-n') + 1] == '10'
        assert cmd[cmd.index('-s') + 1] == '2025-4-1-0-0-0'
        assert cmd[cmd.index('-e') + 1] == '2025-7-1-0-0-0'
        assert cmd[cmd.index('-w') + 1] == '2'

    def test_defaults_workers_to_one(self):
        cmd = build_command('s', 1, 's', 'e')
        assert cmd[cmd.index('-w') + 1] == '1'


@pytest.mark.scripts
@pytest.mark.evaluate_out_of_sample
class TestEvaluateOutOfSampleCli:

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_help_smoke(self, runner: CliRunner):
        result = runner.invoke(evaluate_out_of_sample, ['--help'])
        assert result.exit_code == 0
        assert '--study_name' in result.output
        assert '--num_sets' in result.output
        assert '--n_workers' in result.output

    def test_fails_when_required_options_missing(self, runner: CliRunner):
        result = runner.invoke(evaluate_out_of_sample, [])
        assert result.exit_code != 0

    @patch('scripts.evaluate_out_of_sample.run_evaluate_out_of_sample')
    def test_passes_callback_and_n_workers_to_library(
        self, mock_run, runner: CliRunner
    ):
        # When
        result = runner.invoke(evaluate_out_of_sample, [
            '-sn', 'study_x', '-n', '3',
            '-s', '2025-4-1-0-0-0', '-e', '2025-7-1-0-0-0',
            '-w', '4',
        ])

        # Then
        assert result.exit_code == 0, result.output
        kwargs = mock_run.call_args.kwargs
        assert kwargs['study_name'] == 'study_x'
        assert kwargs['num_sets'] == 3
        assert kwargs['n_workers'] == 4
        assert isinstance(kwargs['progress_callback'], JsonProgressCallback)

    @patch('scripts.evaluate_out_of_sample.run_evaluate_out_of_sample')
    def test_emits_done_with_count_of_emitted_progress(self, mock_run, runner: CliRunner):
        # Given — the library invokes the callback twice during evaluation.
        def fake_run(*, progress_callback, **kwargs):
            progress_callback()
            progress_callback()
        mock_run.side_effect = fake_run

        # When
        result = runner.invoke(evaluate_out_of_sample, [
            '-sn', 'study_x', '-n', '5',
            '-s', '2025-4-1-0-0-0', '-e', '2025-7-1-0-0-0',
        ])

        # Then
        assert result.exit_code == 0, result.output
        lines = result.output.strip().splitlines()
        events = [line.split(' ', 1)[0] for line in lines]
        assert events.count('PROGRESS') == 2
        assert events[-1] == 'DONE'
        last_event, last_payload = lines[-1].split(' ', 1)
        assert json.loads(last_payload) == {'trials': 2}


@pytest.mark.scripts
@pytest.mark.evaluate_out_of_sample
class TestJsonProgressCallback:

    def test_emits_progress_with_incrementing_count(self, capsys):
        # Given
        callback = JsonProgressCallback()

        # When
        callback()
        callback()

        # Then
        lines = capsys.readouterr().out.strip().splitlines()
        assert len(lines) == 2
        for i, line in enumerate(lines, start=1):
            event, payload_json = line.split(' ', 1)
            assert event == 'PROGRESS'
            assert json.loads(payload_json) == {'trial': i}
