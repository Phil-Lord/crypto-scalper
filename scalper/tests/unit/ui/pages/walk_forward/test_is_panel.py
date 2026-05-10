import pytest

from ui.models.walk_forward import StudyDirection, StudySummary
from ui.pages.walk_forward.components.is_panel import (
    IsRunInputs,
    derive_run_inputs,
    validate_is_form,
)


def _summary(name: str) -> StudySummary:
    return StudySummary(
        name=name,
        pair='XXBTZGBP',
        strategy='SmaStrategy',
        trial_count=0,
        best_is=None,
        direction=StudyDirection.MAXIMIZE,
    )


@pytest.mark.ui
@pytest.mark.walk_forward_is_panel
class TestDeriveRunInputs:
    def test_decodes_canonical_study_name(self):
        result = derive_run_inputs(
            _summary('SmaStrategy_XXBTZGBP_20250101-20250401')
        )
        assert result == IsRunInputs(
            raw_pair='BTCGBP',
            strategy='SmaStrategy',
            start='2025-1-1-0-0-0',
            end='2025-4-1-0-0-0',
        )

    def test_returns_none_for_legacy_name_without_window(self):
        '''
        Older studies were named purely by ``Strategy_pair``. The panel must
        return ``None`` so the page can disable the button rather than
        passing garbage into ``start_in_sample``.
        '''
        assert derive_run_inputs(_summary('SmaStrategy_BTCGBP')) is None

    def test_returns_none_for_unknown_pair(self):
        assert derive_run_inputs(
            _summary('SmaStrategy_NOTAPAIR_20250101-20250401')
        ) is None

    def test_returns_none_for_unparseable_dates(self):
        assert derive_run_inputs(
            _summary('SmaStrategy_XXBTZGBP_notadate-20250401')
        ) is None

    def test_round_trips_with_create_study_name(self):
        '''
        The decoded inputs must reconstruct the same study name when fed
        back through ``backtesting_engine.create_study_name`` — that's how
        ``start_in_sample`` resolves which study to extend.
        '''
        from backtesting_engine import create_study_name
        from utils import get_kraken_pair, get_second_timestamp, parse_datetime

        original = 'PrecisionTrendStrategy_XXBTZGBP_20240315-20240920'
        inputs = derive_run_inputs(_summary(original))
        assert inputs is not None

        rebuilt = create_study_name(
            inputs.strategy,
            get_kraken_pair(inputs.raw_pair),
            get_second_timestamp(*parse_datetime(inputs.start)),
            get_second_timestamp(*parse_datetime(inputs.end)),
        )
        assert rebuilt == original


@pytest.mark.ui
@pytest.mark.walk_forward_is_panel
class TestValidateIsForm:
    def test_returns_ints_for_valid_input(self):
        assert validate_is_form('100', '4') == (100, 4)

    def test_strips_whitespace(self):
        assert validate_is_form(' 50 ', '\t2\n') == (50, 2)

    @pytest.mark.parametrize('trials,workers', [('abc', '4'), ('10', 'x'), ('', '4'), (None, '4')])
    def test_rejects_non_integers(self, trials, workers):
        with pytest.raises(ValueError, match='must be integers'):
            validate_is_form(trials, workers)

    @pytest.mark.parametrize('trials,workers', [('0', '4'), ('10', '0'), ('-1', '4'), ('5', '-2')])
    def test_rejects_non_positive(self, trials, workers):
        with pytest.raises(ValueError, match='must be positive'):
            validate_is_form(trials, workers)
