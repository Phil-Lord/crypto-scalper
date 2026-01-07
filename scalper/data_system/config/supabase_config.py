from utils import get_env_var


class SupabaseConfig:
    URL = get_env_var("SUPABASE_URL")
    KEY = get_env_var("SUPABASE_KEY")
