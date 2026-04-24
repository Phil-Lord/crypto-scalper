from nicegui import ui


def render_slot(flex: int = 1) -> ui.element:
    '''
    Renders a flexible slot element.

    :param flex: The slot's relative size, e.g. 1 for equal size, 2 for double size, etc.
    :return: The rendered slot element.
    '''
    return ui.element('div').classes(f'w-full flex-[{flex}] min-h-0 overflow-hidden')
