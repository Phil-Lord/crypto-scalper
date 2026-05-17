import pytest

from data_system.models.out_of_sample_evaluation_model import OutOfSampleEvaluation


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.out_of_sample_evaluation_model
class TestOutOfSampleEvaluation:
    @pytest.fixture
    def sample_evaluation_data(self):
        return {
            'study_name': 'test_study',
            'trial_number': 1,
            'start_timestamp': 1704067200.0,  # 2024-01-01 00:00:00 UTC
            'end_timestamp': 1704153600.0,    # 2024-01-02 00:00:00 UTC
            'geo_mean_balance_ratio': 1.0025
        }

    def test_creates_evaluation_with_all_fields(self, sample_evaluation_data):
        # When
        evaluation = OutOfSampleEvaluation(**sample_evaluation_data)

        # Then
        assert evaluation.study_name == sample_evaluation_data['study_name']
        assert evaluation.trial_number == sample_evaluation_data['trial_number']
        assert evaluation.start_timestamp == sample_evaluation_data['start_timestamp']
        assert evaluation.end_timestamp == sample_evaluation_data['end_timestamp']
        assert evaluation.geo_mean_balance_ratio == sample_evaluation_data['geo_mean_balance_ratio']

    def test_requires_geo_mean_balance_ratio(self):
        # When / Then
        with pytest.raises(TypeError):
            OutOfSampleEvaluation(
                study_name='test_study',
                trial_number=1,
                start_timestamp=1704067200.0,
                end_timestamp=1704153600.0,
            )

    def test_out_of_sample_evaluation_is_frozen(self, sample_evaluation_data):
        # Given
        evaluation = OutOfSampleEvaluation(**sample_evaluation_data)

        # When / Then
        with pytest.raises(AttributeError):
            evaluation.study_name = 'modified_study'
