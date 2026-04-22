import pandas as pd
import plotly.graph_objects as go

from backtesting_engine import BacktestingEngine
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository
from strategy_manager import create_strategy
from utils import get_second_timestamp, parse_datetime, PRECISION_TREND_CONFIG


def run_backtest(symbol, start_date, end_date) -> pd.DataFrame:
    strategy = create_strategy('PrecisionTrendStrategy', PRECISION_TREND_CONFIG)
    repo = SQLAlchemyTradeRepository(SQLAlchemyClient())
    start = get_second_timestamp(*parse_datetime(start_date))
    end = get_second_timestamp(*parse_datetime(end_date))
    engine = BacktestingEngine(symbol, strategy, repo, start, end, interval=1, vectorised=True)
    return engine.run()


def plot_backtest_results(results: pd.DataFrame, figure: go.Figure) -> go.Figure:
    print('Plotting backtest results...')
    return figure
