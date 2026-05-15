from unittest.mock import MagicMock, patch

import optuna
import pandas as pd
import pytest

from utils.optuna_utils import (
    ParsedStudyName,
    STUDY_NAME_FORMAT,
    StudyDirection,
    StudySummary,
    create_study_name,
    get_study_choices,
    list_studies,
    load_study,
    parse_study_name
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

    @patch('utils.optuna_utils.optuna')
    def test_preserves_order_returned_by_optuna(self, mock_optuna):
        ''' The rail relies on creation-order from Optuna, so list_studies
        must not reorder. '''
        mock_optuna.study.StudyDirection.MAXIMIZE = optuna.study.StudyDirection.MAXIMIZE
        mock_optuna.get_all_study_summaries.return_value = [
            _make_optuna_summary(
                'SmaStrategy_BTCGBP_20240101-20240601',
                direction=optuna.study.StudyDirection.MAXIMIZE,
                n_trials=10, best_value=1.1,
            ),
            _make_optuna_summary(
                'PrecisionTrendStrategy_XXBTZGBP_20240601-20241201',
                direction=optuna.study.StudyDirection.MINIMIZE,
                n_trials=20, best_value=0.4,
            ),
        ]

        result = list_studies()

        assert [s.name for s in result] == [
            'SmaStrategy_BTCGBP_20240101-20240601',
            'PrecisionTrendStrategy_XXBTZGBP_20240601-20241201',
        ]
        assert result[0].direction == StudyDirection.MAXIMIZE
        assert result[1].direction == StudyDirection.MINIMIZE


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
class TestLoadStudy:
    @patch('utils.optuna_utils.optuna')
    def test_loads_study_with_default_scalper_application_name(self, mock_optuna):
        mock_optuna.load_study.return_value = 'study-sentinel'

        result = load_study('my-study')

        mock_optuna.storages.RDBStorage.assert_called_once()
        rdb_kwargs = mock_optuna.storages.RDBStorage.call_args.kwargs
        assert rdb_kwargs['engine_kwargs']['connect_args']['application_name'] == 'scalper'
        mock_optuna.load_study.assert_called_once_with(
            study_name='my-study',
            storage=mock_optuna.storages.RDBStorage.return_value,
        )
        assert result == 'study-sentinel'

    @patch('utils.optuna_utils.optuna')
    def test_caller_can_override_application_name(self, mock_optuna):
        ''' Tag the Postgres connection per call site so log readers can
        distinguish OOS-eval vs study-analyser vs UI traffic. '''
        load_study('my-study', application_name='out_of_sample_evaluation')

        rdb_kwargs = mock_optuna.storages.RDBStorage.call_args.kwargs
        assert (
            rdb_kwargs['engine_kwargs']['connect_args']['application_name']
            == 'out_of_sample_evaluation'
        )


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestCreateStudyName:
    def test_emits_canonical_format(self):
        name = create_study_name(
            'SmaStrategy',
            'XXBTZGBP',
            pd.Timestamp('2025-01-01').timestamp(),
            pd.Timestamp('2025-04-01').timestamp(),
        )

        assert name == 'SmaStrategy_XXBTZGBP_20250101-20250401'


@pytest.mark.utils
@pytest.mark.optuna_utils
class TestParseStudyName:
    def test_returns_all_four_fields_from_canonical_name(self):
        parsed = parse_study_name('PrecisionTrendStrategy_XXBTZGBP_20250101-20250401')

        assert parsed.strategy == 'PrecisionTrendStrategy'
        assert parsed.kraken_pair == 'XXBTZGBP'
        assert parsed.start_ts == pd.Timestamp('2025-01-01').timestamp()
        assert parsed.end_ts == pd.Timestamp('2025-04-01').timestamp()

    def test_roundtrips_create_study_name(self):
        start = pd.Timestamp('2025-01-01').timestamp()
        end = pd.Timestamp('2025-04-01').timestamp()
        name = create_study_name('SmaStrategy', 'XXBTZGBP', start, end)

        parsed = parse_study_name(name)

        assert parsed.strategy == 'SmaStrategy'
        assert parsed.kraken_pair == 'XXBTZGBP'
        assert parsed.start_ts == start
        assert parsed.end_ts == end

    def test_returned_dataclass_is_frozen(self):
        parsed = parse_study_name('SmaStrategy_XXBTZGBP_20250101-20250401')

        with pytest.raises(AttributeError):
            parsed.strategy = 'OtherStrategy'

    def test_handles_strategy_name_containing_underscores(self):
        '''
        ``rsplit('_', 2)`` splits on the *last* two underscores so a strategy
        name with internal underscores still parses cleanly.
        '''
        parsed = parse_study_name('My_Custom_Strategy_BTCGBP_20240101-20240601')

        assert parsed.strategy == 'My_Custom_Strategy'
        assert parsed.kraken_pair == 'BTCGBP'

    def test_raises_on_non_canonical_name(self):
        with pytest.raises(ValueError, match='canonical format'):
            parse_study_name('not-a-study-name')

    def test_raises_on_unparseable_date_window(self):
        with pytest.raises(ValueError, match='canonical format'):
            parse_study_name('SmaStrategy_XXBTZGBP_notadate-20250401')

    def test_error_message_quotes_canonical_format(self):
        with pytest.raises(ValueError) as exc:
            parse_study_name('not-a-study-name')

        assert STUDY_NAME_FORMAT in str(exc.value)


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
