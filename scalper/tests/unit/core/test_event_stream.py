import json

import pytest

from core.event_stream import DONE, PROGRESS, StreamEvent, emit, parse


@pytest.mark.core
@pytest.mark.event_stream
class TestParse:
    def test_parses_progress_line(self):
        event = parse('PROGRESS {"trial": 3, "value": 1.2, "best": 1.5}')
        assert event == StreamEvent(
            event=PROGRESS,
            payload={'trial': 3, 'value': 1.2, 'best': 1.5},
        )

    def test_parses_done_line(self):
        event = parse('DONE {"trials": 100}')
        assert event == StreamEvent(event=DONE, payload={'trials': 100})

    def test_returns_none_for_blank_line(self):
        assert parse('') is None

    def test_accepts_arbitrary_event_names(self):
        '''
        The parser is generic — only the line shape matters. Consumers decide
        which event names they care about at dispatch time.
        '''
        assert parse('LOG {"foo": 1}') == StreamEvent(event='LOG', payload={'foo': 1})

    def test_returns_none_for_malformed_json(self):
        assert parse('PROGRESS not-json') is None

    def test_returns_none_when_payload_is_not_object(self):
        assert parse('PROGRESS [1, 2, 3]') is None

    def test_returns_none_when_no_payload(self):
        assert parse('PROGRESS') is None

    def test_strips_trailing_whitespace(self):
        event = parse('PROGRESS {"trial": 0}\n')
        assert event is not None
        assert event.payload == {'trial': 0}


@pytest.mark.core
@pytest.mark.event_stream
class TestEmit:
    def test_writes_event_and_json_payload(self, capsys):
        emit(PROGRESS, {'trial': 3, 'best': 1.5})

        captured = capsys.readouterr()
        assert captured.out == 'PROGRESS {"trial": 3, "best": 1.5}\n'

    def test_writes_done_event(self, capsys):
        emit(DONE, {'trials': 10})

        assert capsys.readouterr().out == 'DONE {"trials": 10}\n'

    def test_accepts_arbitrary_event_names(self, capsys):
        emit('CUSTOM', {'x': 1})

        assert capsys.readouterr().out == 'CUSTOM {"x": 1}\n'

    def test_round_trips_through_parse(self, capsys):
        emit(PROGRESS, {'trial': 0, 'value': 1.1})

        line = capsys.readouterr().out
        assert parse(line) == StreamEvent(
            event=PROGRESS,
            payload={'trial': 0, 'value': 1.1},
        )

    def test_payload_is_valid_json(self, capsys):
        payload = {'a': 1, 'b': None, 'c': [1, 2], 'd': 'hi'}
        emit(PROGRESS, payload)

        line = capsys.readouterr().out
        _, raw = line.strip().split(' ', 1)
        assert json.loads(raw) == payload
