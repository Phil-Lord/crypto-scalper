import pytest

from data_system.clients.sqlalchemy_client import SQLAlchemyClient


@pytest.mark.data_system
@pytest.mark.clients
@pytest.mark.sqlalchemy_client
class TestSQLAlchemyClient:
    @pytest.fixture
    def in_memory_client(self):
        return SQLAlchemyClient(url='sqlite:///:memory:')

    def test_init_creates_engine_with_default_url(self, mocker):
        # Given
        mock_url = 'sqlite:///test_default.db'
        mocker.patch(
            'data_system.clients.sqlalchemy_client.LocalSQLiteConfig.SCALPER_DB_URL', mock_url)

        # When
        client = SQLAlchemyClient()

        # Then
        assert client.engine is not None
        assert str(client.engine.url) == mock_url

    def test_init_creates_engine_with_custom_url(self):
        # Given
        test_url = 'sqlite:///test_custom.db'

        # When
        client = SQLAlchemyClient(url=test_url)

        # Then
        assert client.engine is not None
        assert str(client.engine.url) == test_url

    def test_init_creates_session_maker(self):
        # Given / When
        client = SQLAlchemyClient(url='sqlite:///test_custom.db')

        # Then
        assert client.SessionLocal is not None

    def test_session_context_manager_yields_session(self, in_memory_client):
        # When
        with in_memory_client.session() as session:
            # Then
            assert session is not None

    def test_session_commits_on_success(self, in_memory_client, mocker):
        # Given
        mock_session = mocker.MagicMock()
        in_memory_client.SessionLocal = mocker.MagicMock(return_value=mock_session)

        # When
        with in_memory_client.session():
            pass

        # Then
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_session_rolls_back_on_exception(self, in_memory_client, mocker):
        # Given
        mock_session = mocker.MagicMock()
        in_memory_client.SessionLocal = mocker.MagicMock(return_value=mock_session)

        # When / Then
        with pytest.raises(ValueError):
            with in_memory_client.session():
                raise ValueError('Kaboom!')

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    def test_session_closes_even_on_exception(self, in_memory_client, mocker):
        # Given
        mock_session = mocker.MagicMock()
        in_memory_client.SessionLocal = mocker.MagicMock(return_value=mock_session)

        # When
        try:
            with in_memory_client.session():
                raise RuntimeError('Unexpected error')
        except RuntimeError:
            pass

        # Then
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()
