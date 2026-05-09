'''
Walk-forward UI page (``/walk-forward``).

Studies rail on the left, single detail panel on the right.
The detail panel hosts the in-sample and out-of-sample sections;
this shell renders empty placeholders that WF6/WF7 fill in.

Constructs a single :class:`SQLAlchemyClient` for the page and shares it across
the job and out-of-sample-evaluation repositories so subordinate panels and
service calls can reuse the same connection pool.
'''
from nicegui import ui

from data_system import (
    SQLAlchemyClient,
    SQLAlchemyJobRepository,
    SQLAlchemyOutOfSampleEvaluationRepository,
)
from ui.components import render_header

from .in_sample_tab import InSampleTab
from .out_of_sample_tab import OutOfSampleTab


class WalkForwardPage:
    def __init__(self) -> None:
        ui.dark_mode().enable()
        ui.query('.nicegui-content').classes('p-0 gap-0')  # Remove padding/gap from main content
        ui.query('body').style('overflow: hidden')  # Prevent page scrolling

        client = SQLAlchemyClient()
        self.job_repo = SQLAlchemyJobRepository(client)
        self.oos_repo = SQLAlchemyOutOfSampleEvaluationRepository(client)

        render_header()

        with ui.column().classes('w-full p-4 gap-4').style('height: calc(100vh - 50px)'):
            with ui.tabs().classes('w-full') as tabs:
                is_tab = ui.tab('In-sample optimisation')
                oos_tab = ui.tab('Out-of-sample evaluation')
            with ui.tab_panels(tabs, value=is_tab).classes('w-full flex-1 min-h-0'):
                with ui.tab_panel(is_tab).classes('p-0'):
                    self.in_sample = InSampleTab(self.job_repo)
                with ui.tab_panel(oos_tab).classes('p-0'):
                    self.out_of_sample = OutOfSampleTab(self.job_repo)


@ui.page('/walk-forward')
def walk_forward_page() -> None:
    WalkForwardPage()
