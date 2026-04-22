import pandas as pd
import plotly.graph_objects as go


def run_backtest(symbol, start_date, end_date) -> pd.DataFrame:
    print(f'Running backtest for {symbol} from {start_date} to {end_date}...')
    return pd.DataFrame()


def plot_backtest_results(results: pd.DataFrame, figure: go.Figure) -> go.Figure:
    print('Plotting backtest results...')
    return figure
