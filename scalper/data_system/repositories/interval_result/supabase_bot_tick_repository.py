from data_system.clients import SupabaseClient
from .bot_tick_repository import BotTickRepository


class SupabaseBotTickRepository(BotTickRepository):
    TABLE_NAME = 'bot_ticks'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()
