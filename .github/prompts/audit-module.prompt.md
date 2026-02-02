# Audit Module

Audit the specified module against the project's copilot-instructions.md standards.

## Instructions

1. **Read the module** — All source files in the module directory
2. **Read the tests** — Corresponding test files in `scalper/tests/`
3. **Compare against standards** — Check alignment with copilot-instructions.md

## Checklist

### Universal Standards (Part 1)

#### Python Style
- [ ] **Python 3.12+ syntax** — Using `str | None`, `list[Trade]` (not Optional, List)
- [ ] **Single quotes** — Consistently used for all strings
- [ ] **Type hints** — Present on all function signatures
- [ ] **Import organisation** — Standard lib → Third-party → Local (separated by blank lines)
- [ ] **No unused imports** — All imports are used

#### Models & Data Structures
- [ ] **Frozen dataclasses** — Domain models are `@dataclass(frozen=True)`
- [ ] **Field ordering** — Required fields first, optional/defaulted last
- [ ] **Mutable defaults** — Using `field(default_factory=...)` not bare `[]` or `{}`
- [ ] **Attribute documentation** — All attributes documented in class docstring

#### Documentation
- [ ] **Module has docs** — `/docs/{module}/index.md` exists for significant modules
- [ ] **Docstrings where valuable** — Domain models, public APIs, complex logic, non-obvious parameters
- [ ] **No over-documentation** — Avoid duplicating self-explanatory code
- [ ] **reStructuredText style** — Using `:param`, `:return` format

#### Configuration
- [ ] **No logging.basicConfig()** — Never called in library/service code
- [ ] **Logging only at entry points** — Scripts/main modules configure logging
- [ ] **Environment variables** — Using `get_env_var` utility
- [ ] **Config classes** — Simple containers with class attributes

#### Testing
- [ ] **Test structure** — Classes named `Test{ClassName}`, methods `test_{action}_{condition}_{expectation}`
- [ ] **Given/When/Then** — Pattern used with comments
- [ ] **Hierarchical markers** — Module, category, and class-level markers
- [ ] **Markers registered** — All markers in `pytest.ini`
- [ ] **Makefile target** — `test/{module}` exists
- [ ] **Test coverage depth** — Testing complex behaviors (retry, pagination, errors), not just happy paths
- [ ] **Fixture quality** — Type-hinted, descriptive names, appropriate scope

#### File & Module Naming
- [ ] **Naming conventions** — Following module/file/test naming standards
- [ ] **Public API exports** — `__init__.py` exports the public interface

### Architectural Patterns (Part 2) — When Applicable

#### Repository Pattern
- [ ] **Abstract base** — Interface defines contract
- [ ] **Dependency injection** — Implementation injected with client
- [ ] **Naming** — Follows `{Backend}{Entity}Repository`
- [ ] **Both exported** — Interface and implementations in `__init__.py`

#### Layered Architecture (Client/Service/Connector)
- [ ] **Layer responsibilities** — Each layer has clear purpose
- [ ] **Error handling placement** — Errors handled in appropriate layer, not leaked
- [ ] **Validation at boundaries** — External data validated where it enters
- [ ] **Layers add value** — Not just simple delegation
- [ ] **Consistent return types** — Domain objects vs raw responses clearly separated

#### General Architecture
- [ ] **Dependency injection** — External services injected, not instantiated
- [ ] **Client abstraction** — Third-party SDKs wrapped appropriately
- [ ] **Dependencies flow** — One direction, no circular dependencies

### Architecture Decision Log

- [ ] **Check existing decisions** — Review `/docs/architecture-decision-log.md` for relevant context
- [ ] **Flag new decisions** — Note any non-obvious decisions that should be logged

### Output Format

Provide:

1. **What's aligned** — Brief summary of what follows standards
2. **Issues to fix** — Table of specific issues with file locations
3. **Recommendations** — Any patterns worth adding to instructions

Do NOT fix anything yet — wait for confirmation.
