from supabase import Client, create_client

from data_system.config.supabase_config import SupabaseConfig


class SupabaseClient():
    def get_client(self) -> Client:
        return create_client(SupabaseConfig.URL, SupabaseConfig.KEY)
