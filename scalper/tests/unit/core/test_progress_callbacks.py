import json
from unittest.mock import MagicMock

import optuna
import pytest

from core.progress_callbacks import JsonEvaluationProgressCallback, JsonTrialProgressCallback


@pytest.mark.core
@pytest.mark.progress_callbacks
class TestJsonTrialProgressCallback:

    def test_emits_progress_line_per_trial(self, capsys):
        # Given
        callback = JsonTrialProgressCallback()
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
        callback = JsonTrialProgressCallback()
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


@pytest.mark.core
@pytest.mark.progress_callbacks
class TestJsonEvaluationProgressCallback:

    def test_emits_progress_with_incrementing_count(self, capsys):
        # Given
        callback = JsonEvaluationProgressCallback()

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

    def test_count_tracks_number_of_emissions(self):
        # Given
        callback = JsonEvaluationProgressCallback()

        # When
        callback()
        callback()
        callback()

        # Then
        assert callback.count == 3
