import pytest

from ui.models.walk_forward import (
    StudyDirection,
    StudySummary,
    TrialVerdict,
    TrialWithOos,
)


@pytest.mark.ui
@pytest.mark.ui_models
@pytest.mark.study_direction_enum
class TestStudyDirection:
    def test_values_match_optuna_serialised_form(self):
        assert StudyDirection.MAXIMIZE.value == 'maximize'
        assert StudyDirection.MINIMIZE.value == 'minimize'

    def test_is_string_compatible(self):
        assert StudyDirection.MAXIMIZE == 'maximize'
        assert StudyDirection.MINIMIZE == 'minimize'


@pytest.mark.ui
@pytest.mark.ui_models
@pytest.mark.trial_verdict_enum
class TestTrialVerdict:
    def test_values_use_british_spelling(self):
        assert TrialVerdict.PENDING.value == 'pending'
        assert TrialVerdict.GENERALISES.value == 'generalises'
        assert TrialVerdict.OVERFIT.value == 'overfit'

    def test_is_string_compatible(self):
        assert TrialVerdict.PENDING == 'pending'
        assert TrialVerdict.GENERALISES == 'generalises'
        assert TrialVerdict.OVERFIT == 'overfit'


@pytest.mark.ui
@pytest.mark.ui_models
@pytest.mark.study_summary_model
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
        # When
        summary = StudySummary(**sample_summary_data)

        # Then
        assert summary.name == sample_summary_data['name']
        assert summary.pair == sample_summary_data['pair']
        assert summary.strategy == sample_summary_data['strategy']
        assert summary.trial_count == sample_summary_data['trial_count']
        assert summary.best_is == sample_summary_data['best_is']
        assert summary.direction == StudyDirection.MAXIMIZE

    def test_best_is_can_be_none(self, sample_summary_data):
        # Given
        sample_summary_data['best_is'] = None

        # When
        summary = StudySummary(**sample_summary_data)

        # Then
        assert summary.best_is is None

    def test_summary_is_frozen(self, sample_summary_data):
        # Given
        summary = StudySummary(**sample_summary_data)

        # When / Then
        with pytest.raises(AttributeError):
            summary.trial_count = 99

    def test_requires_all_fields(self):
        # When / Then
        with pytest.raises(TypeError):
            StudySummary(
                name='study',
                pair='XXBTZGBP',
                strategy='SmaStrategy',
                trial_count=5,
            )


@pytest.mark.ui
@pytest.mark.ui_models
@pytest.mark.trial_with_oos_model
class TestTrialWithOos:
    @pytest.fixture
    def sample_trial_data(self):
        return {
            'trial_number': 7,
            'is_value': 1.5,
            'oos_score': 0.9,
            'delta': -0.6,
            'verdict': TrialVerdict.GENERALISES,
            'params': {'sma_period': 20},
        }

    def test_creates_trial_with_all_fields(self, sample_trial_data):
        # When
        trial = TrialWithOos(**sample_trial_data)

        # Then
        assert trial.trial_number == 7
        assert trial.is_value == 1.5
        assert trial.oos_score == 0.9
        assert trial.delta == -0.6
        assert trial.verdict == TrialVerdict.GENERALISES
        assert trial.params == {'sma_period': 20}

    def test_oos_score_and_delta_can_be_none(self, sample_trial_data):
        # Given
        sample_trial_data['oos_score'] = None
        sample_trial_data['delta'] = None
        sample_trial_data['verdict'] = TrialVerdict.PENDING

        # When
        trial = TrialWithOos(**sample_trial_data)

        # Then
        assert trial.oos_score is None
        assert trial.delta is None
        assert trial.verdict == TrialVerdict.PENDING

    def test_trial_is_frozen(self, sample_trial_data):
        # Given
        trial = TrialWithOos(**sample_trial_data)

        # When / Then
        with pytest.raises(AttributeError):
            trial.oos_score = 0.99

    def test_supports_empty_params(self, sample_trial_data):
        # Given
        sample_trial_data['params'] = {}

        # When
        trial = TrialWithOos(**sample_trial_data)

        # Then
        assert trial.params == {}
