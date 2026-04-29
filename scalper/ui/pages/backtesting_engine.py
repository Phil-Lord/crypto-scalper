from nicegui import ui

from core import run_in_thread
from data_system import Job, JobType, SQLAlchemyClient, SQLAlchemyJobRepository

from ui.components import (
    render_chart,
    render_header,
    render_main_content,
    render_sidebar,
    render_slot,
    render_table
)
from ui.services import fetch_trades, get_trades, plot_backtest_results, plot_trades, run_backtest, update_table
from ui.theme import primary_button, sidebar_input, sidebar_select


class BacktestingEnginePage:
    def __init__(self):
        ui.dark_mode().enable()
        ui.query('.nicegui-content').classes('p-0 gap-0')  # Remove padding/gap from main content
        ui.query('body').style('overflow: hidden')  # Prevent page scrolling

        render_header()

        with render_sidebar():
            self.symbol = sidebar_select('Symbol', ['XXBTZGBP', 'XETHZGBP'], 'XXBTZGBP')
            self.start_date = sidebar_input('Start date', '2026-04-01')
            self.end_date = sidebar_input('End date', '2026-04-15')

            ui.space()
            self.load_button = primary_button('Load Trades', on_click=self._load_trades)
            self.fetch_button = primary_button('Fetch Trades', on_click=self._fetch_trades)
            self.backtest_button = primary_button('Run Backtest', on_click=self._run_backtest)

        with render_main_content():
            with render_slot(flex=1.5):
                self.chart = render_chart()
            with render_slot():
                self.grid = render_table()

        self.job_repo = SQLAlchemyJobRepository(SQLAlchemyClient())

    async def _load_trades(self):
        job = Job(job_type=JobType.GET_TRADES)
        self._set_loading(True, self.load_button)

        try:
            trades = await run_in_thread(
                self.job_repo,
                job,
                get_trades,
                self.symbol.value,
                self.start_date.value,
                self.end_date.value
            )
            figure = plot_trades(trades, self.chart.figure)
            self.chart.update_figure(figure)
            update_table(self.grid, None)
        except Exception as e:
            print(f'Error loading trades: {e}')
        finally:
            self._set_loading(False)

    async def _fetch_trades(self):
        if not await self._confirm_fetch():
            return

        job = Job(job_type=JobType.FETCH_TRADES)
        self._set_loading(True, self.fetch_button)

        try:
            existing_trades, new_trades = await run_in_thread(
                self.job_repo,
                job,
                fetch_trades,
                self.symbol.value,
                self.start_date.value,
                self.end_date.value
            )
            figure = plot_trades(existing_trades, self.chart.figure, new_trades)
            self.chart.update_figure(figure)
            update_table(self.grid, None)
        except Exception as e:
            print(f'Error fetching trades: {e}')
        finally:
            self._set_loading(False)

    async def _run_backtest(self):
        job = Job(job_type=JobType.RUN_BACKTEST)
        self._set_loading(True, self.backtest_button)

        try:
            results = await run_in_thread(
                self.job_repo,
                job,
                run_backtest,
                self.symbol.value,
                self.start_date.value,
                self.end_date.value
            )
            figure = plot_backtest_results(results, self.chart.figure)
            self.chart.update_figure(figure)
            update_table(self.grid, results)
        except Exception as e:
            print(f'Error running backtest: {e}')
        finally:
            self._set_loading(False)

    async def _confirm_fetch(self) -> bool:
        with ui.dialog() as dialog, ui.card():
            ui.label('Fetch trades from Kraken?').classes('text-lg font-semibold')
            ui.label(
                f'This will hit the live exchange for {self.symbol.value} between '
                f'{self.start_date.value} and {self.end_date.value}, and write any new '
                f'trades to the local DB.'
            )
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=lambda: dialog.submit(False)).props('flat')
                ui.button('Fetch', on_click=lambda: dialog.submit(True))
        return await dialog

    def _set_loading(self, is_loading: bool, button_clicked: ui.button = None) -> None:
        for button in [self.load_button, self.fetch_button, self.backtest_button]:
            if not is_loading:
                button.props(remove='loading')
                button.enable()
                continue
            if button == button_clicked:
                button.props('loading')
            button.disable()


@ui.page('/')
def backtesting_engine():
    BacktestingEnginePage()
