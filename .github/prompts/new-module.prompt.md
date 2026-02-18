# New Module

Scaffold a new module under `scalper/` following project standards.

## Instructions

1. **Clarify scope** — Confirm module name, purpose, and which architectural patterns apply
   (repository pattern, layered architecture, or simple utilities)
2. **Create directory structure** — See structure below
3. **Create models** — Frozen dataclasses with full docstrings
4. **Create public API** — `__init__.py` exporting only the public interface
5. **Create docs** — `/docs/{module}/index.md` with overview and architecture
6. **Create tests** — Unit test stubs with correct markers and file structure
7. **Register markers** — Add all new markers to `pytest.ini`
8. **Add Makefile targets** — Module-level and category-level targets

---

## Standard Module Structure

### Simple module
```
scalper/{module}/
├── __init__.py          # Public API exports
├── {entity}_model.py    # Domain models
└── {module}.py          # Main logic
```

### Module with multiple backends (repository pattern)
```
scalper/{module}/
├── __init__.py
├── models/
│   └── {entity}_model.py
├── config/
│   └── {backend}_config.py
├── clients/
│   └── {backend}_client.py
└── repositories/
    └── {entity}/
        ├── {entity}_repository.py          # Abstract base
        └── {backend}_{entity}_repository.py  # Implementation
```

### Module with external API (layered architecture)
```
scalper/{module}/
├── __init__.py          # Exports connectors only
├── models/
│   └── {entity}_model.py
├── connectors/          # Public API, domain transformation
│   └── {feature}_connector.py
├── services/            # Platform-specific logic, retry, pagination
│   └── {feature}_service.py
└── api/                 # Low-level HTTP, auth, error parsing
    └── {platform}_api_client.py
```

---

## Test Structure

```
scalper/tests/unit/{module}/
├── __init__.py
└── test_{component}.py
```

Test class markers follow this hierarchy:
```python
@pytest.mark.{module}           # e.g., @pytest.mark.data_system
@pytest.mark.{category}         # e.g., @pytest.mark.repositories
@pytest.mark.{class_level}      # e.g., @pytest.mark.sqlalchemy_trade_repository
class TestSQLAlchemyTradeRepository:
```

---

## Checklist

- [ ] Directory structure created
- [ ] Models are frozen dataclasses with `Attributes:` docstrings
- [ ] `__init__.py` exports only the public interface
- [ ] `/docs/{module}/index.md` created
- [ ] Test directory and `__init__.py` created
- [ ] All markers added to `pytest.ini`
- [ ] `make test/{module}` target added to `scalper/Makefile`
- [ ] Architecture Decision Log updated if non-obvious decisions were made

---

## Notes

- Export only what external consumers need from `__init__.py` — internal utilities stay private
- If the module has >2 sub-categories, add category-level Makefile targets too (`make test/{module}/{category}`)
- Add to `.PHONY` in the Makefile for every new target
