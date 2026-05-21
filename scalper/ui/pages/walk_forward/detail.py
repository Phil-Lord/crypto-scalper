'''
Detail-pane composition for the walk-forward page.

Lays out the right-hand column of the page: context strip across the top,
in-sample row in the middle, out-of-sample row beneath. The IS and OOS rows
are hosted here but their contents come from
:class:`~ui.pages.walk_forward.components.IsPanel` and
:class:`~ui.pages.walk_forward.components.OosPanel`.
'''
from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from . import context_strip

if TYPE_CHECKING:
    from . import WalkForwardPage


def render_detail(page: WalkForwardPage) -> None:
    with ui.column().classes('flex-1 min-w-0 h-full gap-0'):
        page._context_strip = ui.row().classes(
            'w-full items-center gap-6 px-6 py-3 border-b border-neutral-800 no-wrap'
        )
        context_strip.render_context_strip(page)

        page._is_row = ui.column().classes(
            'w-full px-6 py-4 border-b border-neutral-800 gap-2'
        )
        page._oos_row = ui.column().classes(
            'w-full px-6 py-4 flex-1 min-h-0 gap-2'
        )
        page.is_panel.render(page._is_row)
        page.oos_panel.render(page._oos_row)
