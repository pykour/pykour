# Quickstart

This guide creates a minimal Pykour application in under five minutes.

## 1. Create the project directory

```bash
mkdir my-app && cd my-app
```

## 2. Create the application entry point

Create `app.py` in the project root:

```python
from pathlib import Path
from pykour import Pykour

app = Pykour(routes_dir=Path(__file__).parent / "routes")
```

`routes_dir` tells Pykour where to discover route handlers. If omitted, it defaults to a `routes/` subdirectory next to the file that creates the `Pykour` instance.

## 3. Add your first route

Create `routes/route.py`:

```python
async def get():
    return {"message": "Hello, World!"}
```

That's it -- a single async function named `get` handles `GET /`. Pykour automatically serializes the returned dictionary as JSON.

## 4. Start the development server

```bash
pykour run app:app --reload
```

- `app:app` -- the `module:variable` path to your `Pykour` instance.
- `--reload` -- automatically restarts the server when source files change.

You should see output similar to:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

## 5. Test the endpoint

Open your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000) or use `curl`:

```bash
curl http://127.0.0.1:8000
```

Expected response:

```json
{"message": "Hello, World!"}
```

## Adding more routes

Create additional route files to add endpoints. For example, a health check at `/health`:

```
routes/
  route.py          -> GET /
  health/
    route.py        -> GET /health
```

`routes/health/route.py`:

```python
async def get():
    return {"status": "ok"}
```

Each `route.py` can export any combination of `get`, `post`, `put`, `delete`, and `patch` async functions.

## Common CLI options

| Option | Description |
|--------|-------------|
| `--host HOST` | Bind address (default: `127.0.0.1`) |
| `--port PORT` | Bind port (default: `8000`) |
| `--reload` | Auto-reload on file changes |
| `--workers N` | Number of worker processes |
| `--debug` | Enable debug mode (auto-enables reload, verbose logging, tracebacks) |

## Next steps

- Learn about the [Project Structure](project-structure.md) and file-based routing conventions.
- Explore [Request](../core/request.md) and [Response](../core/response.md) handling.
- Add [Middleware](../middleware/index.md) for CORS, authentication, and more.

---

**See also:** [Installation](installation.md) · [Project Structure](project-structure.md)
[← Back to Home](../index.md)
