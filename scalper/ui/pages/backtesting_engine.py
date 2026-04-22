from nicegui import ui

from core import run_in_thread
from data_system import Job, JobType, SQLAlchemyClient, SQLAlchemyJobRepository

from ui.components import render_chart, render_header, render_sidebar
from ui.services import get_trades, plot_backtest_results, plot_trades, run_backtest
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
            self.status_label = ui.label('').classes('text-neutral-400 text-xs')
            self.load_button = primary_button('Load Trades', on_click=self._load_trades)
            self.backtest_button = primary_button('Run Backtest', on_click=self._run_backtest)

        self.chart = render_chart()
        self.job_repo = SQLAlchemyJobRepository(SQLAlchemyClient())

    async def _load_trades(self):
        job = Job(job_type=JobType.GET_TRADES)
        self.load_button.props('loading')
        self.load_button.disable()
        self.status_label.set_text('Loading trades...')

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
            self.status_label.set_text(f'Error: {job.message}')
            print(f'Error loading trades: {e}')
        finally:
            self.load_button.props(remove='loading')
            self.load_button.enable()
            self.status_label.set_text('')

    async def _run_backtest(self):
        job = Job(job_type=JobType.RUN_BACKTEST)
        self.backtest_button.props('loading')
        self.backtest_button.disable()
        self.status_label.set_text('Running backtest...')

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
        except Exception as e:
            self.status_label.set_text(f'Error: {job.message}')
            print(f'Error running backtest: {e}')
        finally:
            self.backtest_button.props(remove='loading')
            self.backtest_button.enable()
            self.status_label.set_text('')


@ui.page('/')
def backtesting_engine():
    BacktestingEnginePage()
