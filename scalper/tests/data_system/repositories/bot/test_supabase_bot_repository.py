import pytest

from data_system.models.bot_model import Bot
from data_system.repositories.bot.supabase_bot_repository import SupabaseBotRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_repository
class TestSupabaseBotRepository:
    @pytest.fixture
    def mock_supabase_client(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def sample_bot(self) -> Bot:
        return Bot(
            id='btc_1m_001',
            pair='XXBTZGBP',
            strategy_name='PrecisionTrendStrategy',
            strategy_version='v1.0.0',
            interval=1,
            parameters={'rsi_period': 14, 'threshold': 30}
        )

    @pytest.fixture
    def mock_response_data(self, sample_bot: Bot) -> dict:
        ''' Returns data as Supabase would - strings for datetimes. '''
        return {
            'id': sample_bot.id,
            'pair': sample_bot.pair,
            'strategy_name': sample_bot.strategy_name,
            'strategy_version': sample_bot.strategy_version,
            'interval': sample_bot.interval,
            'parameters': sample_bot.parameters,
            'created_at': sample_bot.created_at.isoformat()
        }

    def _set_select_response(self, client, data: list) -> None:
        ''' Sets response for: table().select().eq().execute() '''
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = data

    def _set_insert_response(self, client, data: list) -> None:
        ''' Sets response for: table().insert().execute() '''
        client.table.return_value.insert.return_value.execute.return_value.data = data

    def test_get_returns_none_when_bot_not_found(self, mock_supabase_client):
        # Given
        self._set_select_response(mock_supabase_client, [])
        repository = SupabaseBotRepository(mock_supabase_client)

        # When
        result = repository.get('nonexistent_bot')

        # Then
        assert result is None
        mock_supabase_client.table.assert_called_once_with('bots')

    def test_get_returns_bot_when_found(self, mock_supabase_client, sample_bot: Bot, mock_response_data: dict):
        # Given
        self._set_select_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRepository(mock_supabase_client)

        # When
        result = repository.get(sample_bot.id)

        # Then
        assert result is not None
        assert result.id == sample_bot.id
        assert result.pair == sample_bot.pair
        assert result.strategy_name == sample_bot.strategy_name
        assert result.strategy_version == sample_bot.strategy_version
        assert result.interval == sample_bot.interval
        assert result.parameters == sample_bot.parameters
        assert result.created_at == sample_bot.created_at
        mock_supabase_client.table.assert_called_once_with('bots')

    def test_get_calls_select_with_correct_id(self, mock_supabase_client):
        # Given
        self._set_select_response(mock_supabase_client, [])
        repository = SupabaseBotRepository(mock_supabase_client)
        bot_id = 'test_bot_id'

        # When
        repository.get(bot_id)

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.assert_called_once_with('id', bot_id)

    def test_add_inserts_bot_and_returns_result(self, mock_supabase_client, sample_bot: Bot, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRepository(mock_supabase_client)

        # When
        result = repository.add(sample_bot)

        # Then
        assert result.id == sample_bot.id
        assert result.pair == sample_bot.pair
        assert result.strategy_name == sample_bot.strategy_name
        assert result.strategy_version == sample_bot.strategy_version
        assert result.interval == sample_bot.interval
        assert result.parameters == sample_bot.parameters
        assert result.created_at == sample_bot.created_at
        mock_supabase_client.table.assert_called_once_with('bots')

    def test_add_converts_created_at_to_iso_format(self, mock_supabase_client, sample_bot: Bot, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRepository(mock_supabase_client)

        # When
        repository.add(sample_bot)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['created_at'] == sample_bot.created_at.isoformat()
