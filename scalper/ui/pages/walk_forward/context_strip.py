'''
Selected-study summary strip for the walk-forward page.

Renders the strip across the top of the detail pane: the selected study's
name, strategy, pair, trial count, and best in-sample value.
'''
from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from ui.theme import caption, muted

from .components import StatBlock

if TYPE_CHECKING:
    from . import WalkForwardPage


def render_context_strip(page: WalkForwardPage) -> None:
    page._context_strip.clear()
    with page._context_strip:
        study = page._selected_study
        with ui.column().classes('gap-0.5 items-start'):
            caption('Selected study')
            ui.label(study.name if study is not None else '—').classes(
                'text-[13px] font-mono text-neutral-100'
            )
        ui.element('div').classes('h-8 w-px bg-neutral-800')

        if study is None:
            muted('Select or create a study to begin.')
            return

        StatBlock('Strategy', study.strategy or '—')
        StatBlock('Pair', study.pair or '—')
        StatBlock('Trials', f'{study.trial_count:,}')
        StatBlock(
            'Best IS',
            f'{study.best_is:.3f}' if study.best_is is not None else '—',
            highlight=study.best_is is not None,
        )
