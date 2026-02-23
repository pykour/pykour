# Installation

## Requirements

- **Python 3.13+**

## Install with pip

```bash
pip install pykour
```

## Install with uv

```bash
uv add pykour
```

## Optional Dependencies

Pykour keeps its core dependency footprint small. Extra features are available through optional dependency groups:

| Extra | Install command | Description |
|-------|----------------|-------------|
| `cli` | `pip install pykour[cli]` | Interactive CLI helpers (project scaffolding via `questionary`) |

Database drivers and other integrations are installed separately as needed:

| Package | Install command | Description |
|---------|----------------|-------------|
| `aiosqlite` | `pip install aiosqlite` | SQLite async driver |
| `asyncpg` | `pip install asyncpg` | PostgreSQL async driver |
| `aiomysql` | `pip install aiomysql` | MySQL async driver |

For example, to set up a project with PostgreSQL support:

```bash
pip install pykour asyncpg
```

## Development Setup

If you want to contribute to Pykour or run its test suite, clone the repository and install the development dependencies:

```bash
git clone https://github.com/t0k0sh1/pykour.git
cd pykour
uv sync --all-groups
```

This installs all runtime and development dependencies (pytest, ruff, ty, database drivers, etc.).

### Verify the installation

```bash
pykour --version
```

---

**See also:** [Quickstart](quickstart.md) · [Project Structure](project-structure.md)
[← Back to Home](../index.md)
