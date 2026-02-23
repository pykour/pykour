# File-Based Routing

Pykour は Next.js にインスパイアされたファイルベースルーティングを採用しています。`routes/` ディレクトリ内のファイル構造が URL パスに直接マッピングされます。

## 仕組み

アプリケーション起動時に `routes/` ディレクトリが再帰的にスキャンされ、`route.py` ファイルが自動検出されます。各 `route.py` 内のハンドラ関数が対応する URL パスに登録されます。

## ディレクトリ構造と URL マッピング

```
routes/
├── route.py                    → /
├── api/
│   ├── route.py                → /api
│   └── users/
│       ├── route.py            → /api/users
│       └── [id]/
│           └── route.py        → /api/users/{id}
├── health/
│   └── route.py                → /health
└── posts/
    ├── route.py                → /posts
    └── [slug]/
        ├── route.py            → /posts/{slug}
        └── comments/
            └── route.py        → /posts/{slug}/comments
```

## HTTP メソッドハンドラ

各 `route.py` ファイルでは、HTTP メソッドに対応する非同期関数をエクスポートします。サポートされているメソッド名は以下の通りです:

| 関数名 | HTTP メソッド |
|--------|-------------|
| `get` | GET |
| `post` | POST |
| `put` | PUT |
| `delete` | DELETE |
| `patch` | PATCH |
| `head` | HEAD |
| `options` | OPTIONS |

```python
# routes/api/users/route.py
from pykour.request import Request
from pykour.response import JSONResponse

async def get(request: Request) -> JSONResponse:
    """GET /api/users - ユーザー一覧を取得"""
    users = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    return JSONResponse(users)

async def post(request: Request) -> JSONResponse:
    """POST /api/users - ユーザーを作成"""
    data = await request.json()
    return JSONResponse({"id": 3, **data}, status_code=201)
```

## 動的セグメント

ディレクトリ名を `[param]` の形式にすることで、動的 URL セグメントを定義できます。角括弧内の名前がパスパラメータ名になります。

```python
# routes/api/users/[id]/route.py
from pykour.request import Request
from pykour.response import JSONResponse
from pykour.schema import Path

async def get(request: Request, id: int = Path()) -> JSONResponse:
    """GET /api/users/{id} - 特定ユーザーを取得"""
    return JSONResponse({"id": id, "name": "Alice"})

async def delete(request: Request, id: int = Path()) -> JSONResponse:
    """DELETE /api/users/{id} - ユーザーを削除"""
    return JSONResponse({"deleted": id})
```

### ネストされた動的セグメント

複数の動的セグメントをネストすることもできます:

```python
# routes/posts/[slug]/comments/[comment_id]/route.py
from pykour.request import Request
from pykour.response import JSONResponse
from pykour.schema import Path

async def get(
    request: Request,
    slug: str = Path(),
    comment_id: int = Path(),
) -> JSONResponse:
    return JSONResponse({
        "post_slug": slug,
        "comment_id": comment_id,
    })
```

## パスパラメータへのアクセス

パスパラメータにアクセスするには 2 つの方法があります:

### 1. Parameter Injection (推奨)

ハンドラの引数に `Path()` マーカーを使用します。型ヒントに基づいて自動的に型変換されます:

```python
from pykour.schema import Path

async def get(request: Request, id: int = Path()) -> JSONResponse:
    # id は自動的に int に変換される
    return JSONResponse({"id": id})
```

### 2. Request オブジェクト経由

`request.path_params` ディクショナリから直接取得します:

```python
async def get(request: Request) -> JSONResponse:
    id = int(request.path_params["id"])
    return JSONResponse({"id": id})
```

## WebSocket ルート

`route.py` 内に `websocket` 関数をエクスポートすることで、WebSocket エンドポイントを定義できます:

```python
# routes/ws/route.py
from pykour.websocket import WebSocket

async def websocket(ws: WebSocket) -> None:
    await ws.accept()
    async for message in ws.iter_text():
        await ws.send_text(f"Echo: {message}")
```

詳細は [WebSocket](websocket.md) を参照してください。

## See also

- [Parameter Injection](parameter-injection.md) - Path, Query, Body マーカーの詳細
- [Request](request.md) - Request オブジェクトの API
- [WebSocket](websocket.md) - WebSocket ハンドラ
