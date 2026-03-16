from abc import ABC, abstractmethod

from data_system.models import BotOrder


class BotOrderRepository(ABC):
    @abstractmethod
    def add(self, bot_order: BotOrder) -> BotOrder:
        '''
        Adds a new order record.

        :param bot_order: The order record to add.
        :return: The added order record.
        '''
        pass

    @abstractmethod
    def get_by_bot_id(self, bot_id: str) -> list[BotOrder]:
        '''
        Fetches orders for a certain bot ID.

        :param bot_id: Bot ID.
        :return: List of order records.
        '''
        pass

    @abstractmethod
    def update(self, bot_order: BotOrder) -> BotOrder:
        '''
        Updates an existing order record.

        :param bot_order: The order record to update.
        :return: The updated order record.
        '''
        pass
