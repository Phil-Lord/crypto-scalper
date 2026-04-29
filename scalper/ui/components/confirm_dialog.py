from nicegui import ui


async def confirm_dialog(
    title: str,
    message: str,
    confirm_text: str = 'Confirm',
    cancel_text: str = 'Cancel'
) -> bool:
    '''
    Shows a modal confirmation dialog and awaits the user's choice.

    :param title: Heading shown at the top of the dialog.
    :param message: Body text describing the action being confirmed.
    :param confirm_text: Label for the confirm button.
    :param cancel_text: Label for the cancel button.
    :return: True if the user confirmed, False if they cancelled or dismissed.
    '''
    with ui.dialog() as dialog, ui.card():
        ui.label(title).classes('text-lg font-semibold')
        ui.label(message)
        with ui.row().classes('w-full justify-end'):
            ui.button(cancel_text, on_click=lambda: dialog.submit(False)).props('flat')
            ui.button(confirm_text, on_click=lambda: dialog.submit(True))
    return bool(await dialog)
