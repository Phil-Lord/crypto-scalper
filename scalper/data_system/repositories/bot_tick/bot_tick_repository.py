from abc import ABC, abstractmethod

from data_system.models import BotTick


class BotTickRepository(ABC):
    @abstractmethod
    def add(self, result: BotTick) -> BotTick:
        '''
        Adds a new tick record.

        :param result: The tick record to add.

        :return: The added tick record.
        '''
        pass

    @abstractmethod
    def get_by_bot_id(self, bot_id: str) -> list[BotTick]:
        '''
        Fetches ticks for a certain bot ID.

        :param bot_id: Bot ID.

        :return: List of tick dictionaries.
        '''
        pass
