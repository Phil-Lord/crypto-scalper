from data_system.clients import SupabaseClient
from .interval_result_repository import IntervalResultRepository


class SupabaseIntervalResultRepository(IntervalResultRepository):
    TABLE_NAME = 'interval_results'

    def __init__(self) -> None:
        self.client = SupabaseClient()
