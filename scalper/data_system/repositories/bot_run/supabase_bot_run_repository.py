from data_system.clients import SupabaseClient
from .bot_run_repository import BotRunRepository


class SupabaseBotRunRepository(BotRunRepository):
    TABLE_NAME = 'bot_runs'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()
