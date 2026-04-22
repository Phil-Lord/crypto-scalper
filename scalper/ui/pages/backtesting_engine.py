import asyncio

from nicegui import background_tasks, ui

from data_system import Job, JobType, SQLAlchemyClient, SQLAlchemyJobRepository
from core import run_in_thread

from ui.components import build_chart, render_header, render_sidebar
from ui.services import get_trades
from ui.theme import primary_button, sidebar_input, sidebar_select


class BacktestingEnginePage:
    def __init__(self):
        ui.dark_mode().enable()
        render_header()
        self.job_repo = SQLAlchemyJobRepository(SQLAlchemyClient())

        with render_sidebar():
            self.symbol = sidebar_select('Symbol', ['XXBTZGBP', 'XETHZGBP'], 'XXBTZGBP')
            self.start_date = sidebar_input('Start date', '2026-04-01')
            self.end_date = sidebar_input('End date', '2026-04-15')

            ui.space()
            self.status_label = ui.label('').classes('text-neutral-400 text-xs')
            self.load_button = primary_button('Load Trades', on_click=self.load_trades)

        self.chart = ui.plotly(build_chart([])).classes('w-full h-full gap-4')

    async def load_trades(self):
        job = Job(job_type=JobType.GET_TRADES)
        self.load_button.props('loading')
        self.load_button.disable()
        self.status_label.set_text('Loading trades...')
        background_tasks.create(self._run_load_trades(job))

    async def _run_load_trades(self, job: Job):
        try:
            trades = await run_in_thread(
                self.job_repo,
                job,
                get_trades,
                self.symbol.value,
                self.start_date.value,
                self.end_date.value
            )
            self.status_label.set_text('Plotting trades...')
            figure = await asyncio.to_thread(build_chart, trades)
            self.chart.update_figure(figure)
            self.status_label.set_text('')
        except Exception as e:
            self.status_label.set_text(f'Error: {job.message}')
        finally:
            self.load_button.props(remove='loading')
            self.load_button.enable()


@ui.page('/')
def backtesting_engine():
    BacktestingEnginePage()
