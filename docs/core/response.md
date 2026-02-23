---
title: Response
parent: Core
nav_order: 3
---

# Response

Pykour はさまざまなレスポンスタイプを提供しています。全てのレスポンスクラスは基底クラス `Response` を継承しています。

```python
from pykour.response import (
    Response,
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    FileResponse,
    StreamingResponse,
    EventSourceResponse,
    ServerSentEvent,
)
```

## Response

基底レスポンスクラス。全てのレスポンスタイプの親クラスです。

```python
Response(
    content: bytes | str = b"",
    status_code: int = 200,
    headers: dict[str, str] | list[tuple[str, str]] | None = None,
    media_type: str | None = None,
)
```

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `content` | `bytes \| str` | `b""` | レスポンスボディ |
| `status_code` | `int` | `200` | HTTP ステータスコード |
| `headers` | `dict \| list[tuple] \| None` | `None` | レスポンスヘッダー |
| `media_type` | `str \| None` | `None` | Content-Type ヘッダー |

### ヘッダー操作

```python
response = Response("Hello", status_code=200)

# ヘッダーの設定
response.set_header("X-Custom", "value")

# ヘッダーの追加 (重複可)
response.add_header("X-Multi", "value1")
response.add_header("X-Multi", "value2")

# ヘッダーの取得
value = response.get_header("X-Custom")

# ヘッダーの削除
response.remove_header("X-Custom")
```

### Cookie の設定

```python
response.set_cookie(
    name="session_id",
    value="abc123",
    max_age=3600,           # 秒単位の有効期間
    expires=None,           # 有効期限 (GMT 形式)
    path="/",               # Cookie パス
    domain=None,            # Cookie ドメイン
    secure=True,            # HTTPS のみ
    httponly=True,           # JavaScript からアクセス不可
    samesite="Lax",         # SameSite ポリシー
)

# Cookie の削除
response.delete_cookie("session_id")
```

## JSONResponse

JSON データを返すレスポンス。Content-Type は自動的に `application/json` に設定されます。

```python
JSONResponse(
    content: Any = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
)
```

```python
async def get(request: Request) -> JSONResponse:
    return JSONResponse(
        {"message": "Hello, World!"},
        status_code=200,
    )
```

ハンドラから `dict` や `list` を直接返すと、自動的に `JSONResponse` に変換されます:

```python
async def get(request: Request):
    return {"message": "Hello, World!"}
```

## HTMLResponse

HTML コンテンツを返すレスポンス。Content-Type は `text/html; charset=utf-8` です。

```python
HTMLResponse(
    content: bytes | str = "",
    status_code: int = 200,
    headers: dict[str, str] | None = None,
)
```

```python
async def get(request: Request) -> HTMLResponse:
    return HTMLResponse("<h1>Hello, World!</h1>")
```

## PlainTextResponse

プレーンテキストを返すレスポンス。Content-Type は `text/plain; charset=utf-8` です。

```python
PlainTextResponse(
    content: bytes | str = "",
    status_code: int = 200,
    headers: dict[str, str] | None = None,
)
```

```python
async def get(request: Request) -> PlainTextResponse:
    return PlainTextResponse("Hello, World!")
```

## FileResponse

ファイルをストリーミングで返すレスポンス。Content-Type はファイル拡張子から自動検出されます。

```python
FileResponse(
    path: str | Path,
    *,
    status_code: int = 200,
    headers: dict[str, str] | list[tuple[str, str]] | None = None,
    media_type: str | None = None,
    filename: str | None = None,
    chunk_size: int = 65536,
)
```

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `path` | `str \| Path` | (必須) | ファイルパス |
| `media_type` | `str \| None` | `None` | Content-Type (自動検出) |
| `filename` | `str \| None` | `None` | ダウンロード時のファイル名 |
| `chunk_size` | `int` | `65536` | ストリーミングのチャンクサイズ (バイト) |

```python
async def get(request: Request) -> FileResponse:
    return FileResponse(
        "reports/monthly.pdf",
        filename="report.pdf",
    )
```

ファイルが存在しない場合は `FileNotFoundError`、パスがディレクトリの場合は `IsADirectoryError` が発生します。

## StreamingResponse

コンテンツをストリーミングで返すレスポンス。大量のデータを段階的に送信する場合に使用します。

```python
StreamingResponse(
    content: AsyncIterable | Iterable,
    status_code: int = 200,
    headers: dict[str, str] | list[tuple[str, str]] | None = None,
    media_type: str | None = None,
)
```

```python
import asyncio

async def generate():
    for i in range(10):
        yield f"chunk {i}\n"
        await asyncio.sleep(0.1)

async def get(request: Request) -> StreamingResponse:
    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )
```

## EventSourceResponse

Server-Sent Events (SSE) を返すレスポンス。Content-Type は `text/event-stream` に自動設定されます。

```python
EventSourceResponse(
    content: AsyncIterable[ServerSentEvent | str | dict],
    status_code: int = 200,
    headers: dict[str, str] | list[tuple[str, str]] | None = None,
)
```

### ServerSentEvent

SSE イベントのデータ構造です:

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `data` | `Any` | (必須) | イベントデータ (文字列以外は JSON エンコード) |
| `event` | `str \| None` | `None` | イベントタイプ名 |
| `id` | `str \| None` | `None` | イベント ID |
| `retry` | `int \| None` | `None` | 再接続時間 (ミリ秒) |

```python
from pykour.response import EventSourceResponse, ServerSentEvent

async def event_stream():
    for i in range(10):
        yield ServerSentEvent(
            data={"count": i},
            event="update",
            id=f"msg-{i}",
        )
        await asyncio.sleep(1)

async def get(request: Request) -> EventSourceResponse:
    return EventSourceResponse(event_stream())
```

文字列や辞書を直接 yield することもできます:

```python
async def event_stream():
    yield "simple text message"
    yield {"key": "value"}
    yield ServerSentEvent(data="typed event", event="custom")
```

## See also

- [Request](request.md) - リクエストオブジェクト
- [Exception Handling](exception-handling.md) - エラーレスポンス
