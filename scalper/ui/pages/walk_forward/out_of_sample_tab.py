'''
Out-of-sample tab for the walk-forward page.

Owns the OOS sidebar inputs, study-mismatch banner, top-trials preview, progress
label, results table, and the start/stop lifecycle for the evaluation
subprocess.
'''
import asyncio

from nicegui import ui

from data_system import JobRepository
from ui.components import confirm_dialog
from ui.services import (
    get_evaluation_results,
    get_top_trials,
    start_out_of_sample,
)
from ui.theme import primary_button, sidebar_input, sidebar_label, sidebar_select
from utils import get_second_timestamp, list_studies, parse_datetime


OOS_REQUIRED_PAIR = 'XXBTZGBP'
OOS_REQUIRED_STRATEGY = 'PrecisionTrendStrategy'


class OutOfSampleTab:
    def __init__(self, job_repo: JobRepository) -> None:
        self.job_repo = job_repo
        self._task: 'object | None' = None
        self._render()
        self._refresh_preview()

    def _render(self) -> None:
        with ui.row().classes('w-full h-full gap-4 no-wrap'):
            with ui.column().classes(
                'w-64 bg-neutral-900 border border-neutral-800 rounded p-4 gap-3'
            ):
                study_options = self._study_options()
                self.study = sidebar_select(
                    'Study', study_options,
                    value=study_options[0] if study_options else None,
                )
                self.study.on_value_change(lambda _: self._refresh_preview())
                self.num_sets = sidebar_input('Top N', '10')
                self.start = sidebar_input('Start', '2025-4-1-0-0-0')
                self.end = sidebar_input('End', '2025-7-1-0-0-0')
                self.n_workers = sidebar_input('Workers', '1')
                ui.space()
                self.run_button = primary_button('Run evaluation', on_click=self._start)
                self.stop_button = primary_button('Stop', on_click=self._stop)
                self.stop_button.disable()

            with ui.column().classes('flex-1 min-w-0 gap-3'):
                self.banner = ui.label('').classes(
                    'text-sm text-amber-400 bg-amber-900/30 border border-amber-700 '
                    'rounded px-3 py-2'
                )
                self.banner.visible = False

                sidebar_label('Top trials preview')
                self.preview_table = ui.table(
                    columns=[
                        {'name': 'trial_number', 'label': 'Trial', 'field': 'trial_number'},
                        {'name': 'value', 'label': 'In-sample value', 'field': 'value'},
                    ],
                    rows=[],
                    row_key='trial_number',
                ).classes('w-full sticky-header')

                self.progress = ui.label('').classes('text-sm text-neutral-400')

                sidebar_label('Out-of-sample results')
                self.results_table = ui.table(
                    columns=[
                        {'name': 'trial_number', 'label': 'Trial',
                         'field': 'trial_number', 'sortable': True},
                        {'name': 'geo_mean_return', 'label': 'Geo mean return',
                         'field': 'geo_mean_return', 'sortable': True},
                    ],
                    rows=[],
                    row_key='trial_number',
                ).classes('w-full sticky-header')

    def _study_options(self) -> list[str]:
        try:
            return [s.study_name for s in list_studies()]
        except Exception as e:
            ui.notify(f'Could not list studies: {e}', type='negative')
            return []

    def _refresh_preview(self) -> None:
        study_name = self.study.value
        self._update_banner(study_name)

        if not study_name:
            self.preview_table.rows = []
            self.results_table.rows = []
            self.preview_table.update()
            self.results_table.update()
            return

        try:
            num_sets = int(self.num_sets.value)
        except ValueError:
            num_sets = 10

        try:
            top = get_top_trials(study_name, num_sets)
            self.preview_table.rows = [
                {'trial_number': t['trial_number'], 'value': round(t['value'], 6)}
                for t in top
            ]
        except Exception as e:
            ui.notify(f'Could not load top trials: {e}', type='negative')
            self.preview_table.rows = []
        self.preview_table.update()

        self._refresh_results()

    def _refresh_results(self) -> None:
        study_name = self.study.value
        if not study_name:
            self.results_table.rows = []
            self.results_table.update()
            return
        try:
            start_ts = float(get_second_timestamp(*parse_datetime(self.start.value)))
            end_ts = float(get_second_timestamp(*parse_datetime(self.end.value)))
        except Exception:
            return
        try:
            results = get_evaluation_results(study_name, start_ts, end_ts)
        except Exception as e:
            ui.notify(f'Could not load evaluation results: {e}', type='negative')
            return
        self.results_table.rows = [
            {
                'trial_number': r.trial_number,
                'geo_mean_return': round(r.geo_mean_return, 6),
            }
            for r in results
        ]
        self.results_table.update()

    def _update_banner(self, study_name: str | None) -> None:
        if not study_name:
            self.banner.visible = False
            return
        if not study_name.startswith(f'{OOS_REQUIRED_STRATEGY}_{OOS_REQUIRED_PAIR}_'):
            self.banner.text = (
                f'Out-of-sample evaluation is hardcoded to '
                f'{OOS_REQUIRED_STRATEGY} on {OOS_REQUIRED_PAIR}. '
                f'Selecting a different study will run, but the script ignores '
                f'this study name and uses its built-in pair/strategy constants.'
            )
            self.banner.visible = True
        else:
            self.banner.visible = False

    async def _start(self) -> None:
        study_name = self.study.value
        if not study_name:
            ui.notify('Select a study first.', type='warning')
            return
        try:
            num_sets = int(self.num_sets.value)
            n_workers = int(self.n_workers.value)
        except ValueError:
            ui.notify('Top N and workers must be integers.', type='negative')
            return

        self.progress.text = 'Starting…'

        def on_progress(event: dict) -> None:
            payload = event['payload']
            if event['event'] == 'PROGRESS':
                self.progress.text = f'Evaluated trial {payload.get("trial", "?")}…'
            elif event['event'] == 'DONE':
                self.progress.text = f'Done. Evaluated {payload.get("trials", 0)} trials.'

        self._set_running(True)
        self._task = asyncio.create_task(start_out_of_sample(
            study_name, num_sets,
            self.start.value, self.end.value,
            n_workers, self.job_repo, on_progress,
        ))
        try:
            await self._task
        except asyncio.CancelledError:
            self.progress.text = 'Cancelled.'
            ui.notify('Out-of-sample run cancelled.', type='warning')
        except Exception as e:
            ui.notify(f'Out-of-sample run failed: {e}', type='negative')
        finally:
            self._task = None
            self._set_running(False)
            self._refresh_results()

    async def _stop(self) -> None:
        if self._task is None:
            return
        confirmed = await confirm_dialog(
            title='Stop out-of-sample run?',
            message='The subprocess will be terminated.',
            confirm_text='Stop',
        )
        if confirmed:
            self._task.cancel()

    def _set_running(self, running: bool) -> None:
        if running:
            self.run_button.props('loading')
            self.run_button.disable()
            self.stop_button.enable()
        else:
            self.run_button.props(remove='loading')
            self.run_button.enable()
            self.stop_button.disable()
