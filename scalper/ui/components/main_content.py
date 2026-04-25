from nicegui import ui


def render_main_content() -> ui.column:
    '''
    Renders the main content area of the application.

    Height is set to fill the remaining vertical space below the header (100vh - 50px).
    '''
    return ui.column().classes('w-full p-4 gap-4').style('height: calc(100vh - 50px)')
