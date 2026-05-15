from unittest.mock import MagicMock, patch

import optuna
import pytest

from utils.optuna_utils import (
    StudyDirection,
    StudySummary,
    get_study_choices,
    list_studies,
)


def _make_optuna_summary(
    name: str,
    direction: optuna.study.StudyDirection = optuna.study.StudyDirection.MAXIMIZE,
    n_trials: int = 0,
    best_value: float | None = None,
) -> MagicMock:
    summary = MagicMock(spec=optuna.study.StudySummary)
    summary.study_name = name
    summary.direction = direction
    summary.n_trials = n_trials
    if best_value is None:
        summary.best_trial = None
    else:
        best_trial = MagicMock()
        best_trial.value = best_value
        summary.best_trial = best_trial
    return summary


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestListStudies:

    @patch('utils.optuna_utils.optuna')
    def test_parses_pair_and_strategy_from_study_name(self, mock_optuna):
        # Given
        mock_optuna.study.StudyDirection.MAXIMIZE = optuna.study.StudyDirection.MAXIMIZE
        mock_optuna.get_all_study_summaries.return_value = [
            _make_optuna_summary(
                'PrecisionTrendStrategy_XXBTZGBP_20240101-20240601',
                direction=optuna.study.StudyDirection.MAXIMIZE,
                n_trials=42,
                best_value=1.7,
            ),
        ]

        # When
        result = list_studies()

        # Then
        assert result == [StudySummary(
            name='PrecisionTrendStrategy_XXBTZGBP_20240101-20240601',
            pair='XXBTZGBP',
            strategy='PrecisionTrendStrategy',
            trial_count=42,
            best_is=1.7,
            direction=StudyDirection.MAXIMIZE,
        )]

    @patch('utils.optuna_utils.optuna')
    def test_handles_missing_best_trial(self, mock_optuna):
        mock_optuna.study.StudyDirection.MAXIMIZE = optuna.study.StudyDirection.MAXIMIZE
        mock_optuna.get_all_study_summaries.return_value = [
            _make_optuna_summary(
                'SmaStrategy_BTCGBP_20240101-20240601',
                direction=optuna.study.StudyDirection.MAXIMIZE,
                n_trials=0,
                best_value=None,
            ),
        ]

        result = list_studies()

        assert result[0].best_is is None
        assert result[0].trial_count == 0

    @patch('utils.optuna_utils.optuna')
    def test_translates_minimise_direction(self, mock_optuna):
        mock_optuna.study.StudyDirection.MAXIMIZE = optuna.study.StudyDirection.MAXIMIZE
        mock_optuna.get_all_study_summaries.return_value = [
            _make_optuna_summary(
                'SmaStrategy_BTCGBP_20240101-20240601',
                direction=optuna.study.StudyDirection.MINIMIZE,
                n_trials=10,
                best_value=0.2,
            ),
        ]

        result = list_studies()

        assert result[0].direction == StudyDirection.MINIMIZE

    @patch('utils.optuna_utils.optuna')
    def test_returns_empty_pair_and_strategy_for_non_conforming_name(self, mock_optuna):
        mock_optuna.study.StudyDirection.MAXIMIZE = optuna.study.StudyDirection.MAXIMIZE
        mock_optuna.get_all_study_summaries.return_value = [
            _make_optuna_summary(
                'legacy-study-name',
                direction=optuna.study.StudyDirection.MAXIMIZE,
                n_trials=5,
                best_value=1.0,
            ),
        ]

        result = list_studies()

        assert result[0].pair == ''
        assert result[0].strategy == ''
        assert result[0].name == 'legacy-study-name'

    @patch('utils.optuna_utils.optuna')
    def test_returns_empty_when_no_studies(self, mock_optuna):
        mock_optuna.get_all_study_summaries.return_value = []

        assert list_studies() == []

    @patch('utils.optuna_utils.optuna')
    def test_handles_strategy_name_containing_underscores(self, mock_optuna):
        '''
        ``rsplit('_', 2)`` splits on the *last* two underscores so a strategy
        name with internal underscores still parses cleanly.
        '''
        mock_optuna.study.StudyDirection.MAXIMIZE = optuna.study.StudyDirection.MAXIMIZE
        mock_optuna.get_all_study_summaries.return_value = [
            _make_optuna_summary(
                'My_Custom_Strategy_BTCGBP_20240101-20240601',
                direction=optuna.study.StudyDirection.MAXIMIZE,
                n_trials=1,
                best_value=1.0,
            ),
        ]

        result = list_studies()

        assert result[0].strategy == 'My_Custom_Strategy'
        assert result[0].pair == 'BTCGBP'


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestGetStudyChoices:

    @patch('utils.optuna_utils.list_studies')
    def test_wraps_summaries_as_questionary_choices(self, mock_list):
        # Given
        mock_list.return_value = [
            StudySummary(
                name='alpha',
                pair='XXBTZGBP',
                strategy='SmaStrategy',
                trial_count=50,
                best_is=1.0,
                direction=StudyDirection.MAXIMIZE,
            ),
            StudySummary(
                name='beta',
                pair='XETHZGBP',
                strategy='SmaStrategy',
                trial_count=100,
                best_is=None,
                direction=StudyDirection.MAXIMIZE,
            ),
        ]

        # When
        choices = get_study_choices()

        # Then
        assert [c.value for c in choices] == ['alpha', 'beta']
        assert [c.title for c in choices] == ['alpha 50', 'beta 100']


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestStudyDirection:
    def test_values_match_optuna_serialised_form(self):
        assert StudyDirection.MAXIMIZE.value == 'maximize'
        assert StudyDirection.MINIMIZE.value == 'minimize'

    def test_is_string_compatible(self):
        assert StudyDirection.MAXIMIZE == 'maximize'
        assert StudyDirection.MINIMIZE == 'minimize'


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestStudySummary:
    @pytest.fixture
    def sample_summary_data(self):
        return {
            'name': 'PrecisionTrendStrategy_XXBTZGBP_20240101-20240601',
            'pair': 'XXBTZGBP',
            'strategy': 'PrecisionTrendStrategy',
            'trial_count': 42,
            'best_is': 1.7,
            'direction': StudyDirection.MAXIMIZE,
        }

    def test_creates_summary_with_all_fields(self, sample_summary_data):
        summary = StudySummary(**sample_summary_data)

        assert summary.name == sample_summary_data['name']
        assert summary.pair == sample_summary_data['pair']
        assert summary.strategy == sample_summary_data['strategy']
        assert summary.trial_count == sample_summary_data['trial_count']
        assert summary.best_is == sample_summary_data['best_is']
        assert summary.direction == StudyDirection.MAXIMIZE

    def test_best_is_can_be_none(self, sample_summary_data):
        sample_summary_data['best_is'] = None

        summary = StudySummary(**sample_summary_data)

        assert summary.best_is is None

    def test_summary_is_frozen(self, sample_summary_data):
        summary = StudySummary(**sample_summary_data)

        with pytest.raises(AttributeError):
            summary.trial_count = 99

    def test_requires_all_fields(self):
        with pytest.raises(TypeError):
            StudySummary(
                name='study',
                pair='XXBTZGBP',
                strategy='SmaStrategy',
                trial_count=5,
            )
