# New Feature Checklist

Use this prompt to verify a feature is complete and meets project standards before considering it
done.

## Instructions

Review the feature implementation against this checklist. For each unchecked item, either fix it or
explain why it doesn't apply.

## Checklist

### Code Quality
- [ ] **Python 3.12+ syntax** — `str | None`, `list[Type]` (not `Optional`, `List`)
- [ ] **Single quotes** everywhere, including docstrings
- [ ] **British English** — optimise, analyse, serialise, centralise, penalise
- [ ] **Type hints** on all function signatures
- [ ] **No unused imports**
- [ ] **Import order** — stdlib → third-party → local, separated by blank lines

### Models & Data
- [ ] **Frozen dataclasses** for domain models (`@dataclass(frozen=True)`)
- [ ] **Enums** used for fixed value sets, not raw strings
- [ ] **`field(default_factory=...)`** for mutable defaults

### Documentation
- [ ] **Docstrings** on domain models (with `Attributes:` block) and non-obvious public methods
- [ ] **No over-documentation** — skip self-explanatory helpers
- [ ] **reStructuredText** format — `:param`, `:return:` style
- [ ] **`/docs/{module}/`** updated or created if module is significant

### Testing
- [ ] **Unit tests** written for new logic
- [ ] **Test class named** `Test{ClassName}`, **methods** `test_{action}_{condition}_{expectation}`
- [ ] **Given/When/Then** pattern with comments
- [ ] **Pytest markers** applied at class level (module + category + class)
- [ ] **All new markers** registered in `pytest.ini`
- [ ] **Makefile target** added for any new module (`make test/{module}`)
- [ ] **Complex behaviours tested** — retry, error propagation, edge cases (not just happy path)
- [ ] **Integration tests** if the feature spans multiple layers (mock only system boundaries)

### Architecture
- [ ] **`__init__.py`** updated to export new public API (and only public API)
- [ ] **Dependency injection** used — no internal instantiation of external services
- [ ] **Memory-bounded state** if used in a long-running process (`deque(maxlen=N)`)

### Configuration
- [ ] **`logging.basicConfig()` absent** from library code
- [ ] **`os.getenv()`** used in library code (not `load_env()`)

### Housekeeping
- [ ] **Architecture Decision Log** updated if a non-obvious decision was made
- [ ] **Prompt file** created in `.github/prompts/` if the task is now repeatable
