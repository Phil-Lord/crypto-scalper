from supabase import create_client

from data_system.config.supabase_config import SupabaseConfig


class SupabaseClient():
    def __init__(self):
        self = create_client(SupabaseConfig.URL, SupabaseConfig.KEY)
