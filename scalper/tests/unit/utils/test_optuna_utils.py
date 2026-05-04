from unittest.mock import MagicMock, patch

import pytest

from utils.optuna_utils import StudySummary, get_study_choices, list_studies


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestListStudies:

    @patch('utils.optuna_utils.optuna')
    def test_returns_study_summaries(self, mock_optuna):
        # Given
        rows = [('alpha', 50), ('beta', 100)]
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = rows
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = connection
        mock_optuna.storages.RDBStorage.return_value.engine = engine

        # When
        result = list_studies()

        # Then
        assert result == [
            StudySummary(study_name='alpha', n_trials=50),
            StudySummary(study_name='beta', n_trials=100),
        ]

    @patch('utils.optuna_utils.optuna')
    def test_returns_empty_list_when_no_studies(self, mock_optuna):
        # Given
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = []
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = connection
        mock_optuna.storages.RDBStorage.return_value.engine = engine

        # When
        result = list_studies()

        # Then
        assert result == []


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestGetStudyChoices:

    @patch('utils.optuna_utils.list_studies')
    def test_wraps_summaries_as_questionary_choices(self, mock_list):
        # Given
        mock_list.return_value = [
            StudySummary(study_name='alpha', n_trials=50),
            StudySummary(study_name='beta', n_trials=100),
        ]

        # When
        choices = get_study_choices()

        # Then
        assert [c.value for c in choices] == ['alpha', 'beta']
        assert [c.title for c in choices] == ['alpha 50', 'beta 100']
