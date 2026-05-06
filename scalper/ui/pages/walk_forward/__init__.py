'''
Walk-forward UI page (``/walk-forward``).

Two tabs share a single page: in-sample Optuna optimisation, and out-of-sample
evaluation of the resulting top trials. The page itself is a thin shell — each
tab lives in its own module and owns its widgets, lifecycle, and progress
handling.
'''
from nicegui import ui

from data_system import SQLAlchemyClient, SQLAlchemyJobRepository
from ui.components import render_header

from .in_sample_tab import InSampleTab
from .out_of_sample_tab import OutOfSampleTab


class WalkForwardPage:
    def __init__(self) -> None:
        ui.dark_mode().enable()
        ui.query('.nicegui-content').classes('p-0 gap-0')  # Remove padding/gap from main content
        ui.query('body').style('overflow: hidden')  # Prevent page scrolling

        self.job_repo = SQLAlchemyJobRepository(SQLAlchemyClient())

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
