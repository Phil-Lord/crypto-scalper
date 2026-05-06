'''
In-sample tab for the walk-forward page.

Owns the IS sidebar inputs, workers table, and the start/stop lifecycle for the
Optuna optimisation subprocess fan-out.
'''
import asyncio

import pandas as pd
from nicegui import ui

from data_system import JobRepository
from ui.components import confirm_dialog
from ui.services import start_in_sample
from ui.theme import primary_button, sidebar_input, sidebar_label, sidebar_select
from utils import get_kraken_pair, get_second_timestamp, parse_datetime


PAIR_OPTIONS = ['BTCGBP', 'ETHGBP']
STRATEGY_OPTIONS = ['SmaStrategy', 'PrecisionTrendStrategy']


class InSampleTab:
    def __init__(self, job_repo: JobRepository) -> None:
        self.job_repo = job_repo
        self._task: 'object | None' = None
        self._render()

    def _render(self) -> None:
        with ui.row().classes('w-full h-full gap-4 no-wrap'):
            with ui.column().classes(
                'w-64 bg-neutral-900 border border-neutral-800 rounded p-4 gap-3'
            ):
                self.pair = sidebar_select('Pair', PAIR_OPTIONS, PAIR_OPTIONS[0])
                self.strategy = sidebar_select(
                    'Strategy', STRATEGY_OPTIONS, 'PrecisionTrendStrategy'
                )
                self.start = sidebar_input('Start', '2025-1-1-0-0-0')
                self.end = sidebar_input('End', '2025-4-1-0-0-0')
                self.n_trials = sidebar_input('Trials', '100')
                self.n_workers = sidebar_input('Workers', '4')
                ui.space()
                self.start_button = primary_button('Start', on_click=self._start)
                self.stop_button = primary_button('Stop', on_click=self._stop)
                self.stop_button.disable()

            with ui.column().classes('flex-1 min-w-0 gap-3'):
                sidebar_label('Workers')
                self.table = ui.table(
                    columns=[
                        {'name': 'study', 'label': 'Study', 'field': 'study', 'align': 'left'},
                        {'name': 'worker', 'label': 'Worker', 'field': 'worker'},
                        {'name': 'status', 'label': 'Status', 'field': 'status'},
                        {'name': 'latest_trial', 'label': 'Latest trial', 'field': 'latest_trial'},
                        {'name': 'best_value', 'label': 'Best value', 'field': 'best_value'},
                    ],
                    rows=[],
                    row_key='worker',
                ).classes('w-full sticky-header')

    async def _start(self) -> None:
        try:
            n_trials = int(self.n_trials.value)
            n_workers = int(self.n_workers.value)
        except ValueError:
            ui.notify('Trials and workers must be integers.', type='negative')
            return

        study_name = _derive_study_name(
            self.pair.value, self.strategy.value, self.start.value, self.end.value,
        )
        rows = [
            {
                'study': study_name,
                'worker': i + 1,
                'status': 'pending',
                'latest_trial': None,
                'best_value': None,
            }
            for i in range(n_workers)
        ]
        self.table.rows = rows
        self.table.update()

        def on_progress(worker_index: int, event: dict) -> None:
            row = rows[worker_index]
            payload = event['payload']
            if event['event'] == 'PROGRESS':
                row['status'] = 'running'
                if 'trial' in payload:
                    row['latest_trial'] = payload['trial']
                if payload.get('best') is not None:
                    row['best_value'] = round(payload['best'], 6)
            elif event['event'] == 'DONE':
                row['status'] = 'done'
            self.table.update()

        self._set_running(True)
        self._task = asyncio.create_task(start_in_sample(
            self.pair.value,
            self.strategy.value,
            self.start.value,
            self.end.value,
            n_trials,
            n_workers,
            self.job_repo,
            on_progress,
        ))
        try:
            await self._task
        except asyncio.CancelledError:
            for row in rows:
                if row['status'] == 'running':
                    row['status'] = 'cancelled'
            self.table.update()
            ui.notify('In-sample run cancelled.', type='warning')
        except Exception as e:
            ui.notify(f'In-sample run failed: {e}', type='negative')
        finally:
            self._task = None
            self._set_running(False)

    async def _stop(self) -> None:
        if self._task is None:
            return
        confirmed = await confirm_dialog(
            title='Stop in-sample run?',
            message='Subprocesses will be terminated. Optuna keeps completed trials.',
            confirm_text='Stop',
        )
        if confirmed:
            self._task.cancel()

    def _set_running(self, running: bool) -> None:
        if running:
            self.start_button.props('loading')
            self.start_button.disable()
            self.stop_button.enable()
        else:
            self.start_button.props(remove='loading')
            self.start_button.enable()
            self.stop_button.disable()


def _derive_study_name(pair: str, strategy_name: str, start: str, end: str) -> str:
    '''
    Reproduce ``BacktestingEngine`` study naming for display in the IS table.

    Mirrors ``backtesting_engine.parameter_optimisation.create_study_name``;
    kept as a private helper so the page can show the study a worker is writing
    to before the worker emits its first PROGRESS line.
    '''
    try:
        kraken_pair = get_kraken_pair(pair)
        start_ts = get_second_timestamp(*parse_datetime(start))
        end_ts = get_second_timestamp(*parse_datetime(end))
        start_str = pd.to_datetime(start_ts, unit='s').strftime('%Y%m%d')
        end_str = pd.to_datetime(end_ts, unit='s').strftime('%Y%m%d')
        return f'{strategy_name}_{kraken_pair}_{start_str}-{end_str}'
    except Exception:
        return f'{strategy_name}_{pair}'
