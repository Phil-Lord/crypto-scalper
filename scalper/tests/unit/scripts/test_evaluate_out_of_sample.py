import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from core import JsonEvaluationProgressCallback
from scripts.evaluate_out_of_sample import evaluate_out_of_sample


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
        assert isinstance(kwargs['progress_callback'], JsonEvaluationProgressCallback)

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
