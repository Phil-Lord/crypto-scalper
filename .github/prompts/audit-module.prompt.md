# Audit Module

Audit the specified module against the project's copilot-instructions.md standards.

## Instructions

1. **Read the module** — All source files in the module directory
2. **Read the tests** — Corresponding test files in `scalper/tests/`
3. **Compare against standards** — Check alignment with copilot-instructions.md

## Checklist

### Universal Standards (Part 1)

- [ ] **Python style** — Modern syntax, single quotes, type hints, organised imports
- [ ] **Models** — Frozen dataclasses where appropriate
- [ ] **Docstrings** — Present for domain models, public APIs, complex logic
- [ ] **Module docs** — `/docs/{module}/` exists for significant modules
- [ ] **Test structure** — Classes, Given/When/Then, hierarchical markers
- [ ] **Markers registered** — All pytest markers in `pytest.ini`
- [ ] **Makefile targets** — `test/{module}` target exists
- [ ] **Exports** — Public API in `__init__.py`

### Architectural Patterns (Part 2) — When Applicable

- [ ] **Repository pattern** — If data access with multiple backends
- [ ] **Dependency injection** — If external service dependencies
- [ ] **Client abstraction** — If wrapping third-party SDKs

### Output Format

Provide:

1. **What's aligned** — Brief summary of what follows standards
2. **Issues to fix** — Table of specific issues with file locations
3. **Recommendations** — Any patterns worth adding to instructions

Do NOT fix anything yet — wait for confirmation.
