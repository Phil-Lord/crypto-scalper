'''
New-study modal for the walk-forward page.

A footer button on the studies rail opens this dialog. The user picks a pair
and strategy from the registries (no hardcoded option lists), enters a date
window in the project's text-format datetime style, and chooses trials and
workers. On confirm the page kicks off an in-sample run via
``start_in_sample`` under the page-level :class:`PhaseMutex`.

Validation lives in :func:`validate_new_study_form` so it is unit-testable
without instantiating NiceGUI components.
'''
from dataclasses import dataclass

from nicegui import ui

from backtesting_engine import create_study_name
from strategy_manager import STRATEGIES
from ui.theme import primary_button, sidebar_input, sidebar_select
from utils import get_kraken_pair, get_second_timestamp, parse_datetime, raw_to_kraken_pairs


@dataclass(frozen=True)
class NewStudyForm:
    '''
    Validated values from the new-study modal.

    Attributes:
        pair (str): Raw pair symbol, e.g. ``'BTCGBP'``.
        strategy (str): Strategy class name registered in
            ``strategy_manager.factory.STRATEGIES``.
        start (str): Start datetime in ``'YYYY-M-D-h-m-s'`` text format,
            preserved verbatim so it can be passed straight into ``start_in_sample``.
        end (str): End datetime in the same text format.
        n_trials (int): Total Optuna trials to run.
        n_workers (int): Number of parallel worker subprocesses.
    '''
    pair: str
    strategy: str
    start: str
    end: str
    n_trials: int
    n_workers: int


def validate_new_study_form(
    pair: str | None,
    strategy: str | None,
    start: str | None,
    end: str | None,
    n_trials: str | None,
    n_workers: str | None,
) -> NewStudyForm:
    '''
    Validate the raw form values from the dialog and return a
    :class:`NewStudyForm`.

    Field rules:

    * ``pair`` and ``strategy`` are required and must be members of
        ``raw_to_kraken_pairs`` and ``STRATEGIES`` respectively.
    * ``start`` and ``end`` must be parseable by ``utils.parse_datetime``
        (i.e. six dash-separated integers).
    * ``n_trials`` and ``n_workers`` must be positive integers.

    :raises ValueError: With a user-facing message describing the first
        problem encountered.
    '''
    if not pair:
        raise ValueError('Pair is required.')
    if pair not in raw_to_kraken_pairs:
        raise ValueError(f'Unknown pair {pair!r}.')

    if not strategy:
        raise ValueError('Strategy is required.')
    if strategy not in STRATEGIES:
        raise ValueError(f'Unknown strategy {strategy!r}.')

    start_text = (start or '').strip()
    end_text = (end or '').strip()
    if not start_text or not end_text:
        raise ValueError('Start and end datetimes are required.')
    try:
        parse_datetime(start_text)
    except ValueError as e:
        raise ValueError(f'Start datetime is not parseable: {e}')
    try:
        parse_datetime(end_text)
    except ValueError as e:
        raise ValueError(f'End datetime is not parseable: {e}')

    try:
        trials_int = int((n_trials or '').strip())
        workers_int = int((n_workers or '').strip())
    except ValueError:
        raise ValueError('Trials and workers must be integers.')
    if trials_int <= 0 or workers_int <= 0:
        raise ValueError('Trials and workers must be positive.')

    return NewStudyForm(
        pair=pair,
        strategy=strategy,
        start=start_text,
        end=end_text,
        n_trials=trials_int,
        n_workers=workers_int,
    )


def derive_study_name(form: NewStudyForm) -> str:
    '''
    UI-side adapter around ``backtesting_engine.create_study_name`` — converts
    the form's raw pair / text-format datetimes into the engine's expected
    types (kraken pair + second timestamps) and delegates.

    Used by the page to pre-select the new study row in the rail before the
    worker has emitted its first PROGRESS line. Returns an empty string if
    the inputs cannot be converted; the caller falls back to refreshing the
    rail without a target selection.
    '''
    try:
        kraken_pair = get_kraken_pair(form.pair)
        start_ts = get_second_timestamp(*parse_datetime(form.start))
        end_ts = get_second_timestamp(*parse_datetime(form.end))
        return create_study_name(form.strategy, kraken_pair, start_ts, end_ts)
    except Exception:
        return ''


async def show_new_study_dialog() -> NewStudyForm | None:
    '''
    Show the new-study modal and await the user's choice.

    :return: The validated form on confirm, ``None`` if the user cancelled
        or dismissed the dialog. Validation errors are surfaced via
        ``ui.notify`` and leave the dialog open.
    '''
    pair_options = list(raw_to_kraken_pairs.keys())
    strategy_options = list(STRATEGIES.keys())

    with ui.dialog() as dialog, ui.card().classes('w-96 gap-3'):
        ui.label('New study').classes('text-base font-semibold')

        pair_input = sidebar_select('Pair', pair_options, pair_options[0])
        strategy_input = sidebar_select(
            'Strategy', strategy_options, strategy_options[0]
        )
        start_input = sidebar_input('Start', '2025-1-1-0-0-0')
        end_input = sidebar_input('End', '2025-4-1-0-0-0')
        trials_input = sidebar_input('Trials', '100')
        workers_input = sidebar_input('Workers', '4')

        def on_confirm() -> None:
            try:
                form = validate_new_study_form(
                    pair_input.value,
                    strategy_input.value,
                    start_input.value,
                    end_input.value,
                    trials_input.value,
                    workers_input.value,
                )
            except ValueError as e:
                ui.notify(str(e), type='negative')
                return
            dialog.submit(form)

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('Cancel', on_click=lambda: dialog.submit(None)).props('flat')
            primary_button('Create', on_click=on_confirm).classes('w-auto')

    result = await dialog
    return result if isinstance(result, NewStudyForm) else None
