# Testing Conventions

Reference for test code in this project. Universal style rules (Python 3.12+ syntax, single
quotes, British English, type hints) live in `CLAUDE.md` and apply here too.

---

## Layout

- **Unit tests** — `scalper/tests/unit/`, mirroring source structure
  (`strategy_manager/foo.py` → `tests/unit/strategy_manager/test_foo.py`).
- **Integration tests** — `scalper/tests/integration/` as flat files.
- `pytest.ini` sets `pythonpath = scalper` and `testpaths = scalper/tests`, so plain `pytest`
  works from the repo root.

---

## Naming

| Element     | Convention                                | Example                                      |
| ----------- | ----------------------------------------- | -------------------------------------------- |
| Test file   | `test_{module}.py`                        | `test_trade_model.py`                        |
| Test class  | `Test{ClassName}`                         | `TestTrade`                                  |
| Test method | `test_{action}_{condition}_{expectation}` | `test_get_returns_none_when_bot_not_found`   |

Test files import from the direct module path, not the package re-export, so cmd-click resolves
to the definition rather than the re-export.

---

## Structure

Use the **Given/When/Then** pattern with comments when the test benefits from the structure —
multi-step flows, non-trivial setup, or where the action/assertion boundary isn't obvious. Skip
the comments when the test is short and self-evident.

```python
def test_add_inserts_trades(self, mock_client, mock_session, sample_trade: Trade):
    # Given
    repository = SQLAlchemyTradeRepository(mock_client)

    # When
    repository.add([sample_trade])

    # Then
    mock_session.execute.assert_called_once()
```

```python
def test_trade_is_frozen(self, sample_trade_data):
    trade = Trade(**sample_trade_data)
    with pytest.raises(AttributeError):
        trade.price = 60000.0
```

---

## Markers — hierarchical

Apply markers at three levels for granular selection:

```python
@pytest.mark.data_system           # Module
@pytest.mark.repositories          # Category
@pytest.mark.supabase_bot_repository  # Class
class TestSupabaseBotRepository:
    ...
```

**Every new marker must be registered in `pytest.ini`.** Look at the existing marker block to
see the conventions for descriptions.

Run subsets with marker expressions:

```bash
pytest -m data_system
pytest -m "data_system and repositories"
pytest -m integration
```

---

## Integration tests

**Mock only at system boundaries** (HTTP, database connections, file I/O). Let connectors,
services, clients, and transformations all run together. Catches layer-interaction bugs that
unit tests miss.

Markers: `@pytest.mark.integration` (top-level) plus `@pytest.mark.{module}_integration` for the
specific suite.

**Write integration tests when:**
- Multi-layer interactions need verifying (connector → service → client)
- Realistic API data flows through domain transformations
- Parameter passing across multiple function calls
- Error propagation from low-level errors to high-level handlers

**Don't write integration tests for** simple unit-level logic, individual methods in isolation,
or business logic that doesn't span layers.

**Common pitfalls:**
- Mock `time.sleep` so retry loops don't actually delay.
- Make pagination mocks return a terminating sentinel — infinite loops are easy.
- `isinstance(obj, list)` works; `isinstance(obj, list[Type])` does not.
- Account for service-level transformations applied before the result reaches the test
  (e.g. `[:-1]` slicing for pagination cursors).

---

## Coverage philosophy

Test **behaviour**, not just code paths.

- ✅ Retry logic, error propagation, pagination, validation edge cases
- ✅ Integration points between layers
- ❌ Happy-path-only tests with everything mocked
- ❌ Pure delegation (connector calling service with no transformation)

For dual-implementation classes (live + vectorised, see `rules/architecture.md`), include a test
that runs both implementations on the same data and asserts identical output.

---

## Fixtures

- Define fixtures inside the test class when class-specific.
- Type-hint fixture return values.
- Use descriptive names: `sample_trade_data`, `mock_supabase_client`.

```python
@pytest.fixture
def sample_trade(self) -> Trade:
    return Trade(
        trade_id=123456789,
        pair='XXBTZGBP',
        price=50000.0,
        ...
    )
```
