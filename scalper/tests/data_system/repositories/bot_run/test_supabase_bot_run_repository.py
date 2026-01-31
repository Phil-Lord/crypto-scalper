from datetime import datetime, timezone
from uuid import UUID

import pytest

from data_system.models.bot_run_model import BotRun
from data_system.repositories.bot_run.supabase_bot_run_repository import SupabaseBotRunRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_run_repository
class TestSupabaseBotRunRepository:
    @pytest.fixture
    def mock_supabase_client(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def sample_run(self) -> BotRun:
        return BotRun(bot_id='test_bot_id')

    @pytest.fixture
    def completed_run(self) -> BotRun:
        return BotRun(
            bot_id='test_bot_id',
            completed_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def mock_response_data(self, sample_run: BotRun) -> dict:
        ''' Returns data as Supabase would - strings for UUIDs and datetimes. '''
        return {
            'id': str(sample_run.id),
            'bot_id': sample_run.bot_id,
            'started_at': sample_run.started_at.isoformat(),
            'completed_at': None
        }

    @pytest.fixture
    def mock_completed_response_data(self, completed_run: BotRun) -> dict:
        ''' Returns data as Supabase would for a completed run. '''
        return {
            'id': str(completed_run.id),
            'bot_id': completed_run.bot_id,
            'started_at': completed_run.started_at.isoformat(),
            'completed_at': completed_run.completed_at.isoformat()
        }

    def _set_select_response(self, client, data: list) -> None:
        ''' Sets response for: table().select().eq().execute() '''
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = data

    def _set_insert_response(self, client, data: list) -> None:
        ''' Sets response for: table().insert().execute() '''
        client.table.return_value.insert.return_value.execute.return_value.data = data

    def test_get_returns_none_when_run_not_found(self, mock_supabase_client):
        # Given
        self._set_select_response(mock_supabase_client, [])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.get('nonexistent_run_id')

        # Then
        assert result is None
        mock_supabase_client.table.assert_called_once_with('bot_runs')

    def test_get_returns_run_when_found(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_select_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.get(str(sample_run.id))

        # Then
        assert result is not None
        assert result == sample_run
        mock_supabase_client.table.assert_called_once_with('bot_runs')

    def test_get_calls_select_with_correct_id(self, mock_supabase_client):
        # Given
        self._set_select_response(mock_supabase_client, [])
        repository = SupabaseBotRunRepository(mock_supabase_client)
        run_id = 'test_run_id'

        # When
        repository.get(run_id)

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.assert_called_once_with(
            'id', run_id)

    def test_add_inserts_run_and_returns_result(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.add(sample_run)

        # Then
        assert result == sample_run
        mock_supabase_client.table.assert_called_with('bot_runs')

    def test_add_converts_uuid_to_string(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        repository.add(sample_run)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['id'] == str(sample_run.id)

    def test_add_converts_started_at_to_iso_format(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        repository.add(sample_run)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['started_at'] == sample_run.started_at.isoformat()

    def test_add_converts_completed_at_to_iso_format_when_present(self, mock_supabase_client, completed_run: BotRun, mock_completed_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_completed_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        repository.add(completed_run)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['completed_at'] == completed_run.completed_at.isoformat()

    def test_add_does_not_convert_completed_at_when_none(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        repository.add(sample_run)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['completed_at'] is None

    def test_add_parses_response_uuid_to_uuid_object(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.add(sample_run)

        # Then
        assert isinstance(result.id, UUID)
        assert result.id == sample_run.id

    def test_add_parses_response_started_at_to_datetime(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.add(sample_run)

        # Then
        assert isinstance(result.started_at, datetime)
        assert result.started_at == sample_run.started_at

    def test_add_parses_response_completed_at_to_datetime_when_present(self, mock_supabase_client, completed_run: BotRun, mock_completed_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_completed_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.add(completed_run)

        # Then
        assert isinstance(result.completed_at, datetime)
        assert result.completed_at == completed_run.completed_at

    def test_add_leaves_completed_at_as_none_when_null(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.add(sample_run)

        # Then
        assert result.completed_at is None

    def test_get_parses_response_types_correctly(self, mock_supabase_client, sample_run: BotRun, mock_response_data: dict):
        # Given
        self._set_select_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.get(str(sample_run.id))

        # Then
        assert isinstance(result.id, UUID)
        assert isinstance(result.started_at, datetime)
        assert result.id == sample_run.id
        assert result.started_at == sample_run.started_at

    def test_get_parses_completed_at_when_present(self, mock_supabase_client, completed_run: BotRun, mock_completed_response_data: dict):
        # Given
        self._set_select_response(mock_supabase_client, [mock_completed_response_data])
        repository = SupabaseBotRunRepository(mock_supabase_client)

        # When
        result = repository.get(str(completed_run.id))

        # Then
        assert isinstance(result.completed_at, datetime)
        assert result.completed_at == completed_run.completed_at
