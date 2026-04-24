from nicegui import ui

from core import run_in_thread
from data_system import Job, JobType, SQLAlchemyClient, SQLAlchemyJobRepository

from ui.components import render_chart, render_header, render_sidebar, render_table
from ui.services import get_trades, plot_backtest_results, plot_trades, run_backtest, update_table
from ui.theme import primary_button, sidebar_input, sidebar_select


class BacktestingEnginePage:
    def __init__(self):
        ui.dark_mode().enable()
        render_header()

        with render_sidebar():
            self.symbol = sidebar_select('Symbol', ['XXBTZGBP', 'XETHZGBP'], 'XXBTZGBP')
            self.start_date = sidebar_input('Start date', '2026-04-01')
            self.end_date = sidebar_input('End date', '2026-04-15')

            ui.space()
            self.load_button = primary_button('Load Trades', on_click=self._load_trades)
            self.backtest_button = primary_button('Run Backtest', on_click=self._run_backtest)

        self.chart = render_chart()
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
        except Exception as e:
            print(f'Error loading trades: {e}')
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

    def _set_loading(self, is_loading: bool, button_clicked: ui.button = None) -> None:
        for button in [self.load_button, self.backtest_button]:
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
