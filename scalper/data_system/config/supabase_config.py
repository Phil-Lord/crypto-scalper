import os


class SupabaseConfig:
    URL = os.getenv('SUPABASE_URL')
    KEY = os.getenv('SUPABASE_KEY')
