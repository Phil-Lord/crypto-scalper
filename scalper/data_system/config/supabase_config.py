import os


class _SupabaseConfigMeta(type):
    @property
    def URL(cls) -> str | None:
        return os.getenv('SUPABASE_URL')

    @property
    def KEY(cls) -> str | None:
        return os.getenv('SUPABASE_KEY')


class SupabaseConfig(metaclass=_SupabaseConfigMeta):
    pass
