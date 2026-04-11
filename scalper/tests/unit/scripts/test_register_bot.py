from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from scripts.register_bot import register_bot


@pytest.mark.scripts
@pytest.mark.register_bot
class TestRegisterBot:

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @pytest.fixture
    def cli_args(self) -> list[str]:
        return [
            '-i', 'btc_1m_001',
            '-p', 'XXBTZGBP',
            '-sn', 'SmaStrategy',
            '-sv', 'v1.0.0',
            '-int', '1',
            '-par', '{"sma_period": 20}',
        ]

    @patch('scripts.register_bot.BotRepository')
    @patch('scripts.register_bot.Bot')
    def test_register_bot_creates_bot_and_calls_add(
        self, mock_bot_cls, mock_repo_cls, runner: CliRunner, cli_args: list[str]
    ):
        # Given
        mock_bot = MagicMock()
        mock_bot_cls.return_value = mock_bot
        mock_repo = MagicMock()
        mock_repo.add.return_value = mock_bot
        mock_repo_cls.return_value = mock_repo

        # When
        result = runner.invoke(register_bot, cli_args)

        # Then
        assert result.exit_code == 0
        mock_bot_cls.assert_called_once_with(
            'btc_1m_001', 'XXBTZGBP', 'SmaStrategy', 'v1.0.0', 1, {'sma_period': 20},
        )
        mock_repo.add.assert_called_once_with(mock_bot)

    @patch('scripts.register_bot.BotRepository')
    @patch('scripts.register_bot.Bot')
    def test_register_bot_echoes_success_message(
        self, mock_bot_cls, mock_repo_cls, runner: CliRunner, cli_args: list[str]
    ):
        mock_bot = MagicMock()
        mock_bot.__str__ = lambda self: 'Bot(btc_1m_001)'
        mock_repo = MagicMock()
        mock_repo.add.return_value = mock_bot
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(register_bot, cli_args)

        assert result.exit_code == 0
        assert 'Bot registered successfully: Bot(btc_1m_001)' in result.output

    def test_register_bot_fails_when_id_missing(self, runner: CliRunner):
        result = runner.invoke(register_bot, [
            '-p', 'XXBTZGBP', '-sn', 'SmaStrategy', '-sv', 'v1.0.0',
            '-int', '1', '-par', '{}',
        ])
        assert result.exit_code != 0
        assert 'Missing option' in result.output or 'required' in result.output.lower()

    def test_register_bot_fails_when_pair_missing(self, runner: CliRunner):
        result = runner.invoke(register_bot, [
            '-i', 'btc_1m_001', '-sn', 'SmaStrategy', '-sv', 'v1.0.0',
            '-int', '1', '-par', '{}',
        ])
        assert result.exit_code != 0

    def test_register_bot_fails_when_interval_not_int(self, runner: CliRunner):
        result = runner.invoke(register_bot, [
            '-i', 'btc_1m_001', '-p', 'XXBTZGBP', '-sn', 'SmaStrategy',
            '-sv', 'v1.0.0', '-int', 'abc', '-par', '{}',
        ])
        assert result.exit_code != 0

    def test_register_bot_fails_when_parameters_is_invalid_json(self, runner: CliRunner):
        result = runner.invoke(register_bot, [
            '-i', 'btc_1m_001', '-p', 'XXBTZGBP', '-sn', 'SmaStrategy',
            '-sv', 'v1.0.0', '-int', '1', '-par', 'not-json',
        ])
        assert result.exit_code != 0

    @patch('scripts.register_bot.BotRepository')
    @patch('scripts.register_bot.Bot')
    def test_register_bot_propagates_repository_error(
        self, mock_bot_cls, mock_repo_cls, runner: CliRunner, cli_args: list[str]
    ):
        mock_repo = MagicMock()
        mock_repo.add.side_effect = RuntimeError('Connection failed')
        mock_repo_cls.return_value = mock_repo

        result = runner.invoke(register_bot, cli_args)

        assert result.exit_code != 0
