import pytest

from ui.models.walk_forward import StudyDirection, StudySummary


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
