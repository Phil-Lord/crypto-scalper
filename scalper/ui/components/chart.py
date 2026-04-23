from nicegui import ui
import plotly.graph_objects as go


def render_chart() -> ui.plotly:
    layout = go.Layout(
        template='plotly_dark',
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    figure = go.Figure(layout=layout)
    return ui.plotly(figure=figure).classes('w-full h-full gap-4')
