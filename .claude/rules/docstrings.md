# Docstring Conventions

Reference for when and how to write docstrings in this project.

---

## When to write a docstring

**Required:**

- **Domain models (frozen dataclasses)** — Document every attribute in the class docstring.
- **Public API functions and methods** — Repository methods, service entry points, anything
  re-exported from a module's `__init__.py`.
- **Complex logic** — Anything where the WHY isn't obvious from reading the code.
- **Non-obvious parameters** — Document units (nanoseconds vs seconds), formats (Kraken pair
  format), or unusual contracts.

**Skip:**

- **Constants and config values** — The name says it.
- **Simple utility functions** — If the signature and name are clear, a docstring is noise.
- **Internal helpers** — Short private functions with obvious purpose.
- **Simple exception classes** — `KrakenTooManyRequestsError` doesn't need elaboration.
- **Pure delegation** — Methods that just call another method with the same semantics.

**Rule of thumb:** if the docstring would be slower to read than the code, skip it.

---

## Style — reStructuredText

Use `:param`, `:return:` format:

```python
def get(self, pair: str, start: float = None, end: float = None) -> list[Trade]:
    '''
    Fetches trades for a trading pair within a time range.

    :param pair: Trading pair identifier, e.g., 'XXBTZGBP'.
    :param start: Start timestamp (Unix seconds). If None, fetches from earliest.
    :param end: End timestamp (Unix seconds). If None, fetches up to latest.
    :return: List of Trade domain objects.
    '''
```

For dataclasses, document attributes in the class docstring:

```python
@dataclass(frozen=True)
class Trade:
    '''
    Dataclass representing a single trade from the exchange.

    Attributes:
        trade_id (int): Unique trade identifier from the exchange.
        pair (str): Trading pair identifier, e.g., 'XXBTZGBP'.

    Note:
        Primary key is composite (trade_id, pair) since trade IDs are only
        unique per trading pair on Kraken.
    '''
    trade_id: int
    pair: str
    ...
```

Single quotes for docstrings (consistent with the rest of the codebase).

---

## Module documentation

For significant modules, write markdown docs under `/docs/{module}/`.

**Single-page** when the module is simple:

- `index.md` — Overview, architecture, reference

**Multi-page** when `index.md` would exceed ~200 lines:

- `index.md` — Overview, core concepts, architecture (the "what and why")
- `creating-components.md` (or similar) — How-to guides
- `reference.md` — Built-in components, API reference, integration

Keep `index.md` focused on "what and why"; move "how" into separate pages. Add navigation links
at the bottom of `index.md`.

---

## Architecture Decision Log

Record non-obvious architectural decisions in `/docs/architecture-decision-log.md` when:

- The decision isn't clear from the code itself
- Future-you might ask "why did I do it this way?"
- There were trade-offs worth documenting

Examples already in the log: PostgreSQL `DECIMAL(32,12)` truncation, PostgREST float64 rounding
behaviour. New non-obvious decisions go here, not in commit messages.
