import pandas as pd
import plotly.graph_objects as go

MAX_POINTS = 2000


def build_chart(trades: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if len(trades):
        ohlc = convert_to_ohlc(trades)
        fig.add_trace(go.Candlestick(
            x=ohlc['timestamp'],
            open=ohlc['open'],
            high=ohlc['high'],
            low=ohlc['low'],
            close=ohlc['close']
        ))
    fig.update_layout(
        template='plotly_dark',
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig


def convert_to_ohlc(trades: pd.DataFrame) -> pd.DataFrame:
    ''' Converts trades to OHLC, downsampling to a maximum number of points for plotting. '''
    if len(trades) == 0:
        return trades
    interval = max(1, len(trades) // MAX_POINTS)
    trades.set_index('timestamp', inplace=True)
    ohlc = trades['price'].resample(f'{interval}min').ohlc().dropna()
    return ohlc.reset_index()
