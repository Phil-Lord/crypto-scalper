import pytest

from ui.pages.walk_forward.components.new_study_dialog import (
    NewStudyForm,
    derive_study_name,
    validate_new_study_form,
)


@pytest.mark.ui
@pytest.mark.walk_forward_new_study_form
class TestValidateNewStudyForm:
    def test_returns_form_for_valid_input(self):
        form = validate_new_study_form(
            pair='BTCGBP',
            strategy='SmaStrategy',
            start='2025-1-1-0-0-0',
            end='2025-4-1-0-0-0',
            n_trials='100',
            n_workers='4',
        )

        assert form == NewStudyForm(
            pair='BTCGBP',
            strategy='SmaStrategy',
            start='2025-1-1-0-0-0',
            end='2025-4-1-0-0-0',
            n_trials=100,
            n_workers=4,
        )

    def test_strips_whitespace_from_text_fields(self):
        form = validate_new_study_form(
            pair='BTCGBP',
            strategy='SmaStrategy',
            start='  2025-1-1-0-0-0  ',
            end='2025-4-1-0-0-0',
            n_trials=' 50 ',
            n_workers='2',
        )

        assert form.start == '2025-1-1-0-0-0'
        assert form.n_trials == 50

    @pytest.mark.parametrize('pair', [None, ''])
    def test_rejects_missing_pair(self, pair):
        with pytest.raises(ValueError, match='Pair is required'):
            validate_new_study_form(
                pair=pair,
                strategy='SmaStrategy',
                start='2025-1-1-0-0-0',
                end='2025-4-1-0-0-0',
                n_trials='10',
                n_workers='1',
            )

    def test_rejects_unknown_pair(self):
        with pytest.raises(ValueError, match='Unknown pair'):
            validate_new_study_form(
                pair='NOPEGBP',
                strategy='SmaStrategy',
                start='2025-1-1-0-0-0',
                end='2025-4-1-0-0-0',
                n_trials='10',
                n_workers='1',
            )

    @pytest.mark.parametrize('strategy', [None, ''])
    def test_rejects_missing_strategy(self, strategy):
        with pytest.raises(ValueError, match='Strategy is required'):
            validate_new_study_form(
                pair='BTCGBP',
                strategy=strategy,
                start='2025-1-1-0-0-0',
                end='2025-4-1-0-0-0',
                n_trials='10',
                n_workers='1',
            )

    def test_rejects_unknown_strategy(self):
        with pytest.raises(ValueError, match='Unknown strategy'):
            validate_new_study_form(
                pair='BTCGBP',
                strategy='NotAStrategy',
                start='2025-1-1-0-0-0',
                end='2025-4-1-0-0-0',
                n_trials='10',
                n_workers='1',
            )

    @pytest.mark.parametrize('start,end', [('', '2025-1-1-0-0-0'), ('2025-1-1-0-0-0', '')])
    def test_rejects_missing_dates(self, start, end):
        with pytest.raises(ValueError, match='Start and end datetimes are required'):
            validate_new_study_form(
                pair='BTCGBP',
                strategy='SmaStrategy',
                start=start,
                end=end,
                n_trials='10',
                n_workers='1',
            )

    def test_rejects_unparseable_start(self):
        with pytest.raises(ValueError, match='Start datetime is not parseable'):
            validate_new_study_form(
                pair='BTCGBP',
                strategy='SmaStrategy',
                start='not-a-date',
                end='2025-4-1-0-0-0',
                n_trials='10',
                n_workers='1',
            )

    def test_rejects_unparseable_end(self):
        with pytest.raises(ValueError, match='End datetime is not parseable'):
            validate_new_study_form(
                pair='BTCGBP',
                strategy='SmaStrategy',
                start='2025-1-1-0-0-0',
                end='2025/04/01',
                n_trials='10',
                n_workers='1',
            )

    @pytest.mark.parametrize('trials,workers', [('abc', '4'), ('10', 'x')])
    def test_rejects_non_integer_trials_or_workers(self, trials, workers):
        with pytest.raises(ValueError, match='must be integers'):
            validate_new_study_form(
                pair='BTCGBP',
                strategy='SmaStrategy',
                start='2025-1-1-0-0-0',
                end='2025-4-1-0-0-0',
                n_trials=trials,
                n_workers=workers,
            )

    @pytest.mark.parametrize('trials,workers', [('0', '4'), ('10', '0'), ('-1', '4')])
    def test_rejects_non_positive_trials_or_workers(self, trials, workers):
        with pytest.raises(ValueError, match='must be positive'):
            validate_new_study_form(
                pair='BTCGBP',
                strategy='SmaStrategy',
                start='2025-1-1-0-0-0',
                end='2025-4-1-0-0-0',
                n_trials=trials,
                n_workers=workers,
            )


@pytest.mark.ui
@pytest.mark.walk_forward_new_study_form
class TestDeriveStudyName:
    def test_matches_create_study_name_format(self):
        form = NewStudyForm(
            pair='BTCGBP',
            strategy='SmaStrategy',
            start='2025-1-1-0-0-0',
            end='2025-4-1-0-0-0',
            n_trials=100,
            n_workers=4,
        )

        assert derive_study_name(form) == 'SmaStrategy_XXBTZGBP_20250101-20250401'
