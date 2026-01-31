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
            'end_timestamp': 1704153600.0     # 2024-01-02 00:00:00 UTC
        }

    def test_creates_evaluation_with_required_fields(self, sample_evaluation_data):
        # When
        evaluation = GeneralisationEvaluation(**sample_evaluation_data)

        # Then
        assert evaluation.study_name == sample_evaluation_data['study_name']
        assert evaluation.trial_number == sample_evaluation_data['trial_number']
        assert evaluation.start_timestamp == sample_evaluation_data['start_timestamp']
        assert evaluation.end_timestamp == sample_evaluation_data['end_timestamp']

    def test_final_balance_defaults_to_none(self, sample_evaluation_data):
        # When
        evaluation = GeneralisationEvaluation(**sample_evaluation_data)

        # Then
        assert evaluation.final_balance is None

    def test_geo_mean_return_defaults_to_none(self, sample_evaluation_data):
        # When
        evaluation = GeneralisationEvaluation(**sample_evaluation_data)

        # Then
        assert evaluation.geo_mean_return is None

    def test_creates_evaluation_with_final_balance(self, sample_evaluation_data):
        # Given
        final_balance = 1050.50

        # When
        evaluation = GeneralisationEvaluation(
            **sample_evaluation_data,
            final_balance=final_balance
        )

        # Then
        assert evaluation.final_balance == final_balance

    def test_creates_evaluation_with_geo_mean_return(self, sample_evaluation_data):
        # Given
        geo_mean = 1.0025

        # When
        evaluation = GeneralisationEvaluation(
            **sample_evaluation_data,
            geo_mean_return=geo_mean
        )

        # Then
        assert evaluation.geo_mean_return == geo_mean

    def test_creates_evaluation_with_all_optional_fields(self, sample_evaluation_data):
        # Given
        final_balance = 1100.00
        geo_mean = 1.005

        # When
        evaluation = GeneralisationEvaluation(
            **sample_evaluation_data,
            final_balance=final_balance,
            geo_mean_return=geo_mean
        )

        # Then
        assert evaluation.final_balance == final_balance
        assert evaluation.geo_mean_return == geo_mean

    def test_generalisation_evaluation_is_frozen(self, sample_evaluation_data):
        # Given
        evaluation = GeneralisationEvaluation(**sample_evaluation_data)

        # When / Then
        with pytest.raises(AttributeError):
            evaluation.study_name = 'modified_study'
