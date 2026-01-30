import pytest

from data_system.models.generalisation_evaluation_model import GeneralisationEvaluation


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.generalisation_evaluation_model
class TestGeneralisationEvaluation:
    def test_creates_evaluation_with_required_fields(self):
        # Given
        study_name = 'test_study'
        trial_number = 1
        start_timestamp = 1704067200.0  # 2024-01-01 00:00:00 UTC
        end_timestamp = 1704153600.0    # 2024-01-02 00:00:00 UTC

        # When
        evaluation = GeneralisationEvaluation(
            study_name=study_name,
            trial_number=trial_number,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp
        )

        # Then
        assert evaluation.study_name == study_name
        assert evaluation.trial_number == trial_number
        assert evaluation.start_timestamp == start_timestamp
        assert evaluation.end_timestamp == end_timestamp
        assert evaluation.final_balance is None
        assert evaluation.geo_mean_return is None
