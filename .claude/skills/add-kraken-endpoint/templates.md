# Add-Kraken-Endpoint Templates

Copy the relevant block, drop it into the file path noted, and replace every `{{placeholder}}`
with the new endpoint's specifics. Templates are intentionally minimal — extend them where the
endpoint genuinely needs more (e.g. pagination, multiple required params, complex domain
mapping).

`{{name}}` is snake_case (`withdraw_status`); `{{Name}}` is PascalCase (`WithdrawStatus`).

---

## Service

Path: `scalper/exchange_connector/services/{{name}}_service.py`

```python
from typing import Any

from .kraken_service import KrakenService


class {{Name}}Service(KrakenService):
    def {{method_name}}(self, {{args}}) -> dict[str, Any]:
        '''
        {{One-line summary of what the endpoint returns.}}

        :param {{arg}}: {{description}}.
        :return: {{description of dict shape — or note that it's the raw Kraken payload}}.
        '''
        self.validate_pair({{pair_arg}})  # only if the endpoint takes a trading pair
        params = {
            '{{kraken_param}}': {{value}},
        }
        return self.make_request('{{HTTP_METHOD}}', '/0/{{public_or_private}}/{{Endpoint}}', params)
```

For a paginated endpoint, see `trades_service.py`: loop with a moving cursor, terminate on a
sentinel returned by Kraken (e.g. `result['last']`), and use `tqdm` for progress.

---

## Connector

Path: `scalper/exchange_connector/connectors/{{name}}_connector.py`

Use `FetchConnector` for read-only endpoints, `PlaceConnector` for endpoints that mutate
exchange state.

```python
from .base_connectors import FetchConnector
from exchange_connector.api import KrakenApiClient
from exchange_connector.models import {{Name}}Result  # only if a model was added
from exchange_connector.services import {{Name}}Service


class {{Name}}Connector(FetchConnector):
    def __init__(self, client: KrakenApiClient | None = None):
        self.client = client or KrakenApiClient()
        self.service = {{Name}}Service(self.client)

    def fetch(self, {{args}}) -> {{Name}}Result:
        '''
        {{One-line summary.}}

        :param {{arg}}: {{description}}.
        :return: {{Name}}Result domain object.
        '''
        raw = self.service.{{method_name}}({{args}})
        return self._to_domain(raw)

    def _to_domain(self, raw: dict) -> {{Name}}Result:
        '''
        Convert the raw Kraken response to a {{Name}}Result domain object.

        :param raw: Raw API response from Kraken.
        :return: {{Name}}Result domain object.
        :raises ValueError: If the response structure is invalid.
        '''
        try:
            return {{Name}}Result(
                {{field_a}}={{coerce}}(raw['{{kraken_key_a}}']),
                {{field_b}}={{coerce}}(raw['{{kraken_key_b}}']),
            )
        except (KeyError, ValueError, TypeError, IndexError, AttributeError) as e:
            raise ValueError(f'Failed to parse {{name}} response: {raw}. Error: {e}')
```

For dict pass-through endpoints (no domain model), drop `_to_domain`, add
`from typing import Any` to the imports, and have `fetch` return the service result directly:

```python
def fetch(self, {{args}}) -> dict[str, Any]:
    '''
    {{One-line summary.}}

    :param {{arg}}: {{description}}.
    :return: Raw Kraken response payload.
    '''
    return self.service.{{method_name}}({{args}})
```

See `ticker_connector.py` for a working example.

---

## Domain model

Path: `scalper/exchange_connector/models/{{name}}_result.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class {{Name}}Result:
    '''
    Dataclass representing the result of the Kraken {{Name}} endpoint.

    Attributes:
        {{field_a}} ({{type_a}}): {{description}}.
        {{field_b}} ({{type_b}}): {{description}}.

    Note:
        This is an exchange domain model, not a database entity. For persisting
        any of these fields, map to the relevant data_system model.
    '''
    {{field_a}}: {{type_a}}
    {{field_b}}: {{type_b}}
```

---

## Connector tests

Append this class to `scalper/tests/unit/exchange_connector/connectors/test_connectors.py`.
Imports already present at the top of that file — only add what's missing.

```python
@pytest.mark.exchange_connector
@pytest.mark.connectors
@pytest.mark.{{name}}_connector
class Test{{Name}}Connector:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    @pytest.fixture
    def raw_response(self):
        return {
            '{{kraken_key_a}}': {{example_value_a}},
            '{{kraken_key_b}}': {{example_value_b}},
        }

    def test_init_with_injected_client(self, mock_client):
        connector = {{Name}}Connector(client=mock_client)
        assert connector.client == mock_client

    def test_init_creates_default_client_when_none_provided(self):
        connector = {{Name}}Connector()
        assert isinstance(connector.client, KrakenApiClient)

    def test_fetch_returns_domain_object(self, mock_client, raw_response):
        # Given
        connector = {{Name}}Connector(client=mock_client)
        connector.service = Mock()
        connector.service.{{method_name}}.return_value = raw_response

        # When
        result = connector.fetch({{call_args}})

        # Then
        assert isinstance(result, {{Name}}Result)
        assert result.{{field_a}} == {{expected_a}}

    def test_to_domain_raises_on_missing_field(self, mock_client):
        # Given
        connector = {{Name}}Connector(client=mock_client)
        malformed = {'{{kraken_key_a}}': {{example_value_a}}}  # missing kraken_key_b

        # When / Then
        with pytest.raises(ValueError, match='Failed to parse {{name}} response'):
            connector._to_domain(malformed)
```

---

## Service tests

Append this class to `scalper/tests/unit/exchange_connector/services/test_services.py`.

```python
@pytest.mark.exchange_connector
@pytest.mark.services
@pytest.mark.{{name}}_service
class Test{{Name}}Service:
    @pytest.fixture
    def mock_client(self):
        return Mock(spec=KrakenApiClient)

    @pytest.fixture
    def service(self, mock_client):
        return {{Name}}Service(mock_client)

    def test_{{method_name}}_calls_endpoint_with_correct_params(self, service, mock_client):
        # Given
        mock_client.make_request.return_value = {
            'result': {{example_result}},
            'error': []
        }

        # When
        service.{{method_name}}({{call_args}})

        # Then
        mock_client.make_request.assert_called_once_with(
            '{{HTTP_METHOD}}',
            '/0/{{public_or_private}}/{{Endpoint}}',
            {'{{kraken_param}}': {{value}}},
        )

    def test_{{method_name}}_validates_pair(self, service):  # only if endpoint takes a pair
        with pytest.raises(ValueError, match='Trading pair'):
            service.{{method_name}}('bad pair!')
```
