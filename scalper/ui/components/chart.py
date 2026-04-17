import pandas as pd
import plotly.graph_objects as go

from ui.theme import GREEN_BRIGHT


def build_chart(trades: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if len(trades):
        fig.add_trace(go.Scatter(
            x=trades['timestamp'],
            y=trades['price'],
            mode='lines',
            line=dict(color=GREEN_BRIGHT)
        ))
    fig.update_layout(
        template='plotly_dark',
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig
