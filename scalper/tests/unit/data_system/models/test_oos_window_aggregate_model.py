import pytest

from data_system.models.oos_window_aggregate_model import OosWindowAggregate


@pytest.mark.data_system
@pytest.mark.models
@pytest.mark.oos_window_aggregate_model
class TestOosWindowAggregate:
    @pytest.fixture
    def sample_aggregate_data(self):
        return {
            'start': 1704067200.0,
            'end': 1704153600.0,
            'best_oos': 0.85,
            'generalised_count': 3,
            'overfit_count': 2,
        }

    def test_creates_aggregate_with_all_fields(self, sample_aggregate_data):
        # When
        aggregate = OosWindowAggregate(**sample_aggregate_data)

        # Then
        assert aggregate.start == sample_aggregate_data['start']
        assert aggregate.end == sample_aggregate_data['end']
        assert aggregate.best_oos == sample_aggregate_data['best_oos']
        assert aggregate.generalised_count == sample_aggregate_data['generalised_count']
        assert aggregate.overfit_count == sample_aggregate_data['overfit_count']

    def test_requires_all_fields(self):
        # When / Then
        with pytest.raises(TypeError):
            OosWindowAggregate(
                start=1.0,
                end=2.0,
                best_oos=0.5,
            )

    def test_aggregate_is_frozen(self, sample_aggregate_data):
        # Given
        aggregate = OosWindowAggregate(**sample_aggregate_data)

        # When / Then
        with pytest.raises(AttributeError):
            aggregate.best_oos = 0.99

    def test_supports_zero_counts(self, sample_aggregate_data):
        # Given
        sample_aggregate_data['generalised_count'] = 0
        sample_aggregate_data['overfit_count'] = 0

        # When
        aggregate = OosWindowAggregate(**sample_aggregate_data)

        # Then
        assert aggregate.generalised_count == 0
        assert aggregate.overfit_count == 0
