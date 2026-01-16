---
name: pykour-implement
description: Implementation workflow for pykour project. Use when implementing new features, fixing bugs, or modifying code in pykour. Ensures code quality by requiring tests and passing all checks (pytest, ruff, ty).
---

# Pykour Implementation Workflow

## Workflow

1. **Implement code changes**
   - Create or modify source files in `src/pykour/`
   - Follow existing code patterns and conventions

2. **Update tests**
   - Add new test cases for new functionality
   - Modify existing tests if behavior changes
   - Test files in `tests/` directory, named `test_<module>.py`

3. **Run quality checks** (all must pass)
   ```bash
   uv run pytest          # All tests must pass
   uv run ruff check src/ tests/  # No linting errors
   uv run ty check src/   # No type errors
   ```

4. **Fix any failures**
   - If pytest fails: fix code or update tests
   - If ruff fails: run `uv run ruff check --fix src/ tests/` or fix manually
   - If ty fails: add type annotations or fix type errors

## Completion Criteria

Implementation is complete when ALL of the following pass:
- `uv run pytest` - 0 failures
- `uv run ruff check src/ tests/` - "All checks passed!"
- `uv run ty check src/` - "All checks passed!"

## Project Structure

```
src/pykour/
├── __init__.py      # Exports
├── application.py   # Pykour ASGI app
├── request.py       # Request wrapper
├── response.py      # Response classes
├── types.py         # Type definitions
└── py.typed         # PEP 561 marker

tests/
├── test_application.py
├── test_request.py
├── test_response.py
└── test_types.py
```
