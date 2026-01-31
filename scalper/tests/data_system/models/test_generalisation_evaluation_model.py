import pytest

from data_system.models.generalisation_evaluation_model import GeneralisationEvaluation


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.generalisation_evaluation_model
class TestGeneralisationEvaluation:
    @pytest.fixture
    def sample_evaluation_data(self):
        return {
            'study_name': 'test_study',
            'trial_number': 1,
            'start_timestamp': 1704067200.0,  # 2024-01-01 00:00:00 UTC
            'end_timestamp': 1704153600.0,    # 2024-01-02 00:00:00 UTC
            'final_balance': 1050.50,
            'geo_mean_return': 1.0025
        }

    def test_creates_evaluation_with_all_fields(self, sample_evaluation_data):
        # When
        evaluation = GeneralisationEvaluation(**sample_evaluation_data)

        # Then
        assert evaluation.study_name == sample_evaluation_data['study_name']
        assert evaluation.trial_number == sample_evaluation_data['trial_number']
        assert evaluation.start_timestamp == sample_evaluation_data['start_timestamp']
        assert evaluation.end_timestamp == sample_evaluation_data['end_timestamp']
        assert evaluation.final_balance == sample_evaluation_data['final_balance']
        assert evaluation.geo_mean_return == sample_evaluation_data['geo_mean_return']

    def test_requires_final_balance(self):
        # When / Then
        with pytest.raises(TypeError):
            GeneralisationEvaluation(
                study_name='test_study',
                trial_number=1,
                start_timestamp=1704067200.0,
                end_timestamp=1704153600.0,
                geo_mean_return=1.0025
            )

    def test_requires_geo_mean_return(self):
        # When / Then
        with pytest.raises(TypeError):
            GeneralisationEvaluation(
                study_name='test_study',
                trial_number=1,
                start_timestamp=1704067200.0,
                end_timestamp=1704153600.0,
                final_balance=1050.50
            )

    def test_generalisation_evaluation_is_frozen(self, sample_evaluation_data):
        # Given
        evaluation = GeneralisationEvaluation(**sample_evaluation_data)

        # When / Then
        with pytest.raises(AttributeError):
            evaluation.study_name = 'modified_study'
