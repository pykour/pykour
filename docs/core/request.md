---
title: Request
parent: Core
nav_order: 2
---

# Request

`Request` クラスは ASGI スコープをラップし、HTTP リクエストの情報にアクセスするための API を提供します。

```python
from pykour.request import Request
```

## プロパティ

| プロパティ | 型 | 説明 |
|-----------|-----|------|
| `method` | `str` | HTTP メソッド (`GET`, `POST` 等) |
| `path` | `str` | リクエストパス |
| `query_string` | `bytes` | 生のクエリ文字列 |
| `headers` | `dict[str, str]` | リクエストヘッダー |
| `scheme` | `str` | URL スキーム (`http`, `https`) |
| `server` | `tuple[str, int] \| None` | サーバーのホストとポート |
| `http_version` | `str` | HTTP バージョン (`1.1`, `2`) |
| `scope` | `Scope` | 生の ASGI スコープ |
| `path_params` | `dict[str, str]` | URL パスパラメータ |
| `state` | `State` | リクエストごとの状態オブジェクト |
| `user` | `Any` | 認証後のユーザー情報 (ミドルウェアで設定) |
| `cookies` | `dict[str, str]` | リクエストの Cookie |

## リクエストボディ

### body()

生のリクエストボディをバイト列として取得します:

```python
async def post(request: Request) -> JSONResponse:
    raw = await request.body()
    # raw: bytes
    return JSONResponse({"size": len(raw)})
```

### json()

リクエストボディを JSON としてパースします:

```python
async def post(request: Request) -> JSONResponse:
    data = await request.json()
    # data: dict[str, Any]
    return JSONResponse({"received": data})
```

### form()

フォームデータを取得します (`multipart/form-data` および `application/x-www-form-urlencoded`):

```python
async def post(request: Request) -> JSONResponse:
    form_data = await request.form()
    return JSONResponse({"name": form_data["name"]})
```

## クエリパラメータ

### query_params

クエリ文字列をパースした辞書を返します。同じキーに複数の値がある場合はリストになります:

```python
# GET /search?q=pykour&tag=web&tag=python
async def get(request: Request) -> JSONResponse:
    params = await request.query_params()
    # params: {"q": "pykour", "tag": ["web", "python"]}
    return JSONResponse(params)
```

## Cookie

### cookies

全ての Cookie を辞書として取得します:

```python
async def get(request: Request) -> JSONResponse:
    all_cookies = request.cookies
    return JSONResponse({"cookies": all_cookies})
```

### get_cookie(name)

特定の Cookie を名前で取得します:

```python
async def get(request: Request) -> JSONResponse:
    session_id = request.get_cookie("session_id")
    return JSONResponse({"session": session_id})
```

## State

`request.state` は、ミドルウェアやハンドラ間でリクエストスコープのデータを共有するためのオブジェクトです:

```python
# ミドルウェアで設定
async def auth_middleware(request, call_next):
    request.state.user_id = "user-123"
    return await call_next(request)

# ハンドラで参照
async def get(request: Request) -> JSONResponse:
    user_id = request.state.user_id
    return JSONResponse({"user_id": user_id})
```

## User

`request.user` は JWT 認証ミドルウェアなどによって設定されるユーザー情報です:

```python
async def get(request: Request) -> JSONResponse:
    # JWT ミドルウェア適用後に利用可能
    user = request.user
    return JSONResponse({"user": user})
```

## See also

- [Parameter Injection](parameter-injection.md) - リクエストデータの自動注入
- [File-Based Routing](routing.md) - パスパラメータの定義
- [Response](response.md) - レスポンスの作成
