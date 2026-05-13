'''
Line-delimited ``EVENT {json}`` stream between a subprocess and its parent.

Producers call :func:`emit` and Parents call :func:`parse`.

Event names are free-form — :data:`PROGRESS` / :data:`DONE`
are the conventional ones; add more constants as needed.
'''
import json
import sys
from dataclasses import dataclass


PROGRESS = 'PROGRESS'
DONE = 'DONE'


@dataclass(frozen=True)
class StreamEvent:
    '''
    A single parsed event from the subprocess event stream.

    Attributes:
        event (str): Event name — typically one of the module-level constants
            (:data:`PROGRESS`, :data:`DONE`) but any non-empty token is valid.
        payload (dict): JSON-decoded payload object emitted by the producer.
    '''
    event: str
    payload: dict


def emit(event: str, payload: dict) -> None:
    '''
    Write one ``EVENT {json-payload}`` line to stdout and flush.

    :param event: Event name — :data:`PROGRESS`, :data:`DONE`, or any other
        token the consumer recognises.
    :param payload: JSON-serialisable mapping describing the event.
    '''
    sys.stdout.write(f'{event} {json.dumps(payload)}\n')
    sys.stdout.flush()


def parse(line: str) -> StreamEvent | None:
    '''
    Parse one stdout line emitted by a producer.

    Returns a :class:`StreamEvent` if the line is a valid event, else ``None``.
    '''
    if not line:
        return None
    parts = line.strip().split(' ', 1)
    if len(parts) != 2:
        return None
    event, raw_payload = parts
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return StreamEvent(event=event, payload=payload)
