from typing import Literal

from nicegui import ui


GREEN_LIGHT = '#3ecf8e'   # icons
GREEN_BRIGHT = '#03c574'  # links
GREEN_DARK = '#016339'    # buttons

# Dimmed candle colours for already-loaded ('existing') trades on the
# backtesting chart. Plotly needs hex literals rather than Tailwind classes,
# so the chart greys live here alongside ``GREEN_*`` instead of as loose
# literals in ``ui/services/trades.py``.
CHART_DIM_INCREASING = '#9ca3af'
CHART_DIM_DECREASING = '#4b5563'

# Compact uppercase label styles used across the walk-forward page. ``CAPTION``
# is the smallest, dimmest variant (context-strip captions, ``StatBlock``
# labels, sidebar field labels). ``MINOR_HEADER`` is one step up and used for
# sub-section dividers (e.g. ``OOS WINDOWS``, ``TOP TRIALS``, ``WORKERS``).
CAPTION_CLASSES = 'text-[10px] uppercase tracking-wider text-neutral-500'
MINOR_HEADER_CLASSES = 'text-[11px] uppercase tracking-wider text-neutral-400 font-semibold'

# Small mono-spaced label text — metadata captions, counts, trial values, and
# inline readouts across the walk-forward page. Owns the *size* only: one 11px
# scale, replacing the former 10/11/12/13px drift. Compose the colour at the
# call site (``f'{MONO_CAPTION_CLASSES} text-neutral-400'``) — mono colour
# choices are intentionally local (e.g. emerald/red verdict counts).
MONO_CAPTION_CLASSES = 'text-[11px] font-mono'

# Muted body copy — empty-state placeholders and secondary captions
# (e.g. 'No studies yet.'). See :func:`muted`.
MUTED_TEXT_CLASSES = 'text-xs text-neutral-500'

# Standard hairline grey for separators, rails, and panel borders. Compose
# with a Tailwind side: ``f'border-b {BORDER}'``, ``f'border-r {BORDER}'``.
# :func:`separator` renders the filled-rule variant of the same grey.
BORDER = 'border-neutral-800'


PillStatus = Literal['running', 'pending', 'done', 'error', 'cancelled']

_PILL_CLASSES: dict[str, str] = {
    'running': 'bg-amber-900/40 text-amber-300 border-amber-700/60',
    'pending': 'bg-neutral-800 text-neutral-400 border-neutral-700',
    'done': 'bg-emerald-900/40 text-emerald-300 border-emerald-700/60',
    'error': 'bg-red-900/40 text-red-300 border-red-700/60',
    'cancelled': 'bg-neutral-800 text-neutral-500 border-neutral-700',
}


def sidebar_label(text: str) -> ui.label:
    return ui.label(text).classes('text-xs text-neutral-400 uppercase tracking-wide')


def caption(text: str) -> ui.label:
    '''
    Tiny dimmed uppercase caption — context-strip captions, ``StatBlock``
    labels, and sidebar field labels. Thin wrapper over :data:`CAPTION_CLASSES`
    for the common case of a freshly created label.
    '''
    return ui.label(text).classes(CAPTION_CLASSES)


def muted(text: str) -> ui.label:
    '''
    Muted body copy for empty-state placeholders (e.g. 'No studies yet.').
    Callers may append layout classes (padding) to the returned label.
    '''
    return ui.label(text).classes(MUTED_TEXT_CLASSES)


def nav_link(text: str, target: str) -> ui.link:
    '''
    Header navigation link. Keeps the link styling for the app header in one
    place so new top-level pages get a consistent affordance.
    '''
    return ui.link(text, target).classes(
        'text-neutral-300 text-sm cursor-pointer no-underline'
    )


def separator() -> ui.element:
    '''
    Horizontal hairline rule that fills the remaining width of a heading row —
    the divider after a :func:`SectionTitle` label or a minor section header.
    Filled-rule variant of the :data:`BORDER` grey.
    '''
    return ui.element('div').classes('flex-1 h-px bg-neutral-800')


def sidebar_input(label: str, value: str = '') -> ui.input:
    return ui.input(label=label, value=value).classes('w-full')


def sidebar_select(label: str, options: list, value: str = '') -> ui.select:
    return ui.select(label=label, options=options, value=value).classes('w-full')


def primary_button(text: str, on_click: callable = None) -> ui.button:
    return ui.button(text, color=GREEN_DARK, on_click=on_click).classes('w-full text-white')


def stop_button(on_click: callable = None) -> ui.button:
    '''
    Full-width red STOP button used by the IS and OOS panels to cancel an
    in-flight run. Wired into ``PhaseMutex.cancel`` indirectly via the panel's
    ``_on_stop`` confirmation flow.
    '''
    return ui.button(
        '■ STOP', color='red-9', on_click=on_click
    ).classes('w-full text-white')


def StatusPill(status: PillStatus, label: str | None = None) -> ui.label:
    '''
    Small status chip used across the walk-forward page
    (rail rows, section headers, worker tiles).

    :param status: One of ``running`` / ``pending`` / ``done`` / ``error`` / ``cancelled``.
        Drives the colour scheme.
    :param label: Optional override for the displayed text.
        Defaults to the upper-cased status name.
    '''
    if status not in _PILL_CLASSES:
        raise ValueError(
            f'Unknown StatusPill status {status!r}; '
            f'expected one of {sorted(_PILL_CLASSES)}'
        )
    text = (label if label is not None else status).upper()
    return ui.label(text).classes(
        'inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider '
        f'rounded border {_PILL_CLASSES[status]}'
    )


def SectionTitle(
    number: str | int,
    label: str,
    pill: tuple[PillStatus, str | None] | None = None,
) -> None:
    '''
    Two-digit number prefix, label, horizontal rule, and an optional trailing
    :func:`StatusPill`. Used as the heading for sections within the
    walk-forward page (e.g. ``01 IN-SAMPLE``, ``02 OUT-OF-SAMPLE``).

    :param number: Section number — passed through verbatim, so callers
        usually pass ``'01'`` / ``'02'`` to get zero-padded display.
    :param label: Section label (rendered upper-case).
    :param pill: Optional ``(status, label)`` tuple to render a trailing status pill.
        ``label`` may be ``None`` to use the status name.
    '''
    with ui.row().classes('w-full items-center gap-2 no-wrap'):
        ui.label(str(number)).classes('text-xs font-mono text-neutral-500')
        ui.label(label).classes('text-xs uppercase tracking-wider text-neutral-300 font-semibold')
        separator()
        if pill is not None:
            status, pill_label = pill
            StatusPill(status, pill_label)
