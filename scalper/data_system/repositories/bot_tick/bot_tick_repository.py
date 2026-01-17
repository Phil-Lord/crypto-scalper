from abc import ABC, abstractmethod

from data_system.models import BotTick


class BotTickRepository(ABC):
    @abstractmethod
    def add(self, bot_tick: BotTick) -> BotTick:
        '''
        Adds a new tick record.

        :param bot_tick: The tick record to add.
        :return: The added tick record.
        '''
        pass

    @abstractmethod
    def get_by_bot_id(self, bot_id: str) -> list[BotTick]:
        '''
        Fetches ticks for a certain bot ID.

        :param bot_id: Bot ID.
        :return: List of tick records.
        '''
        pass
