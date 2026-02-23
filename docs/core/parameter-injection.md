---
title: Parameter Injection
parent: Core
nav_order: 4
---

# Parameter Injection

Pykour はハンドラ関数の引数に対して、型ヒントとマーカーデフォルトに基づいたパラメータの自動注入を行います。

## マーカー一覧

| マーカー | ソース | インポート |
|---------|--------|----------|
| `Path()` | URL パスセグメント | `from pykour.schema import Path` |
| `Query()` | URL クエリ文字列 | `from pykour.schema import Query` |
| `Body()` | JSON リクエストボディ | `from pykour.schema import Body` |
| `Form()` | フォームデータ | `from pykour.schema import Form` |
| `File()` | アップロードファイル | `from pykour.schema import File` |
| `Depends()` | 依存性注入 | `from pykour.di import Depends` |

## Path()

URL の動的セグメント `[param]` からパスパラメータを抽出します。型ヒントに基づいて自動的に型変換されます。

```python
from pykour.schema import Path

# routes/users/[id]/route.py
async def get(request: Request, id: int = Path()) -> JSONResponse:
    return JSONResponse({"user_id": id})
```

バリデーション制約も指定できます:

```python
async def get(request: Request, id: int = Path(ge=1)) -> JSONResponse:
    return JSONResponse({"user_id": id})
```

## Query()

URL クエリ文字列からパラメータを抽出します。

```python
from pykour.schema import Query

# GET /users?page=2&limit=20
async def get(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, le=100),
) -> JSONResponse:
    return JSONResponse({"page": page, "limit": limit})
```

### Query() のオプション

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `default` | `Any` | デフォルト値 |
| `alias` | `str \| None` | クエリパラメータ名のエイリアス |
| `ge` | `int \| float \| None` | 以上 (>=) |
| `le` | `int \| float \| None` | 以下 (<=) |
| `gt` | `int \| float \| None` | より大きい (>) |
| `lt` | `int \| float \| None` | より小さい (<) |
| `min_length` | `int \| None` | 最小文字列長 |
| `max_length` | `int \| None` | 最大文字列長 |
| `pattern` | `str \| None` | 正規表現パターン |

エイリアスの使用例:

```python
async def get(
    request: Request,
    page_num: int = Query(default=1, alias="page"),
) -> JSONResponse:
    # ?page=3 で page_num=3 として受け取る
    return JSONResponse({"page": page_num})
```

### Convention-based Query

`Path()`, `Query()` などのマーカーを省略した場合、パスパラメータに一致しない引数は自動的にクエリパラメータとして扱われます:

```python
# page と limit は自動的にクエリパラメータとして注入される
async def get(request: Request, page: int = 1, limit: int = 10):
    return {"page": page, "limit": limit}
```

## Body()

JSON リクエストボディからデータを抽出します。`Schema` クラスと組み合わせてバリデーションを行うことができます。

### Schema による型安全なボディ

```python
from pykour.schema import Schema, Field, Body

class CreateUserSchema(Schema):
    name: str
    email: str = Field(pattern=r".+@.+\..+")
    age: int = Field(ge=0, le=150)

async def post(
    request: Request,
    data: CreateUserSchema = Body(),
) -> JSONResponse:
    return JSONResponse({
        "name": data.name,
        "email": data.email,
        "age": data.age,
    }, status_code=201)
```

### 生の dict アクセス

```python
async def post(
    request: Request,
    data: dict = Body(),
) -> JSONResponse:
    return JSONResponse(data)
```

## Form()

`multipart/form-data` または `application/x-www-form-urlencoded` のフォームフィールドを抽出します。

```python
from pykour.schema import Form

async def post(
    username: str = Form(),
    email: str = Form(default=""),
) -> JSONResponse:
    return JSONResponse({"username": username, "email": email})
```

### Form() のオプション

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `default` | `Any` | (必須) | デフォルト値 |
| `alias` | `str \| None` | `None` | フォームフィールド名のエイリアス |
| `description` | `str \| None` | `None` | OpenAPI ドキュメント用の説明 |
| `media_type` | `str` | `"application/x-www-form-urlencoded"` | 期待するメディアタイプ |

## File()

`multipart/form-data` からアップロードファイルを受け取ります。

```python
from pykour.schema import File

# 単一ファイル
async def post(avatar: UploadFile = File()) -> JSONResponse:
    content = await avatar.read()
    return JSONResponse({
        "filename": avatar.filename,
        "size": len(content),
    })

# 複数ファイル
async def post(documents: list[UploadFile] = File()) -> JSONResponse:
    return JSONResponse({"count": len(documents)})
```

### File() のオプション

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `default` | `Any` | (必須) | デフォルト値 |
| `alias` | `str \| None` | `None` | フォームフィールド名のエイリアス |
| `description` | `str \| None` | `None` | OpenAPI ドキュメント用の説明 |
| `max_size` | `int \| None` | `None` | 最大ファイルサイズ (バイト) |
| `allowed_types` | `list[str] \| None` | `None` | 許可する MIME タイプのリスト |

バリデーション制約付きの例:

```python
async def post(
    image: UploadFile = File(
        max_size=5 * 1024 * 1024,  # 5MB
        allowed_types=["image/jpeg", "image/png"],
    ),
) -> JSONResponse:
    content = await image.read()
    return JSONResponse({"size": len(content)})
```

## Depends()

依存性注入コンテナからサービスを注入します。詳細は [Dependency Injection](dependency-injection.md) を参照してください。

```python
from pykour.di import Depends

class UserService:
    async def get_user(self, user_id: int):
        return {"id": user_id, "name": "Alice"}

async def get(
    request: Request,
    id: int = Path(),
    user_service: UserService = Depends(),
) -> JSONResponse:
    user = await user_service.get_user(id)
    return JSONResponse(user)
```

## 型変換

パスパラメータとクエリパラメータは型ヒントに基づいて自動変換されます。サポートされている型:

| 型 | 変換例 |
|-----|-------|
| `int` | `"42"` → `42` |
| `float` | `"3.14"` → `3.14` |
| `bool` | `"true"` → `True` |
| `str` | そのまま |
| `uuid.UUID` | `"550e8400-..."` → `UUID(...)` |
| `datetime` | ISO 8601 文字列 → `datetime` |
| `date` | `"2024-01-15"` → `date(2024, 1, 15)` |

## See also

- [Schema Validation](schema-validation.md) - Body バリデーションの詳細
- [Dependency Injection](dependency-injection.md) - Depends() の詳細
- [File-Based Routing](routing.md) - パスパラメータの定義
