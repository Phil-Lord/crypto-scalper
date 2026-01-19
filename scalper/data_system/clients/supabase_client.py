from typing import Any

from supabase import Client, create_client

from data_system.config.supabase_config import SupabaseConfig


class SupabaseClient:
    '''
    A thin wrapper around the Supabase Client that handles configuration.

    Uses the proxy pattern to delegate all method calls to the underlying Client,
    allowing consumers to use it directly: `client = SupabaseClient()`.
    '''

    _client: Client

    def __init__(self) -> None:
        self._client = create_client(SupabaseConfig.URL, SupabaseConfig.KEY)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
