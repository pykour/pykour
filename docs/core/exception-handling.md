# Exception Handling

Pykour は包括的な例外ハンドリングシステムを提供しています。組み込みの HTTP 例外クラスとカスタム例外ハンドラの登録が可能です。

## HTTPException

全ての HTTP エラーの基底クラスです。

```python
from pykour.exceptions import HTTPException

HTTPException(
    detail: str | None = None,
    status_code: int | None = None,
    headers: dict[str, str] | None = None,
)
```

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `detail` | `str \| None` | エラーメッセージ (クラスデフォルトを使用する場合は None) |
| `status_code` | `int \| None` | HTTP ステータスコード (クラスデフォルトを使用する場合は None) |
| `headers` | `dict \| None` | 追加レスポンスヘッダー |

```python
from pykour.exceptions import HTTPException

# 基底クラスを直接使用
raise HTTPException(detail="Something went wrong", status_code=500)
```

## 組み込み例外クラス

よく使われる HTTP ステータスコードに対応する例外クラスが用意されています:

### 4xx Client Errors

| クラス | ステータスコード | 説明 |
|--------|--------------|------|
| `BadRequestException` | 400 | 不正なリクエスト |
| `UnauthorizedException` | 401 | 認証が必要 |
| `ForbiddenException` | 403 | アクセス禁止 |
| `NotFoundException` | 404 | リソースが見つからない |
| `MethodNotAllowedException` | 405 | 許可されていないメソッド |
| `ConflictException` | 409 | 競合 |
| `UnprocessableEntityException` | 422 | 処理できないエンティティ |
| `TooManyRequestsException` | 429 | リクエスト制限超過 |

### 5xx Server Errors

| クラス | ステータスコード | 説明 |
|--------|--------------|------|
| `InternalServerErrorException` | 500 | サーバー内部エラー |
| `NotImplementedException` | 501 | 未実装 |
| `BadGatewayException` | 502 | 不正なゲートウェイ |
| `ServiceUnavailableException` | 503 | サービス利用不可 |
| `GatewayTimeoutException` | 504 | ゲートウェイタイムアウト |

### 使用例

```python
from pykour.exceptions import NotFoundException, ForbiddenException

async def get(request: Request, id: int = Path()) -> JSONResponse:
    user = await find_user(id)
    if user is None:
        raise NotFoundException(f"User {id} not found")
    if not user["active"]:
        raise ForbiddenException("User account is deactivated")
    return JSONResponse(user)
```

ヘッダー付きの例外:

```python
from pykour.exceptions import UnauthorizedException

raise UnauthorizedException(
    detail="Invalid token",
    headers={"WWW-Authenticate": "Bearer"},
)
```

## カスタム例外ハンドラ

### @app.exception_handler デコレータ

特定の例外タイプに対するカスタムハンドラを登録します:

```python
from pykour import Pykour, JSONResponse
from pykour.exceptions import NotFoundException

app = Pykour()

@app.exception_handler(NotFoundException)
async def handle_not_found(request, exc):
    return JSONResponse(
        {"error": exc.detail, "path": request.path},
        status_code=404,
    )
```

### add_exception_handler メソッド

デコレータの代わりにメソッドで登録することもできます:

```python
async def handle_value_error(request, exc):
    return JSONResponse(
        {"error": str(exc)},
        status_code=400,
    )

app.add_exception_handler(ValueError, handle_value_error)
```

### カスタム例外クラス

独自の例外クラスを定義してハンドラを登録できます:

```python
from pykour.exceptions import NotFoundException

class ItemNotFoundError(NotFoundException):
    def __init__(self, item_id: int):
        self.item_id = item_id
        super().__init__(f"Item {item_id} not found")

@app.exception_handler(ItemNotFoundError)
async def handle_item_not_found(request, exc):
    return JSONResponse(
        {"error": exc.detail, "item_id": exc.item_id},
        status_code=404,
    )
```

## MRO ベースのハンドラ解決

例外ハンドラは Python のメソッド解決順序 (MRO) に基づいて検索されます。より具体的な例外クラスのハンドラが優先されます。

```python
# 基底クラスのハンドラ
@app.exception_handler(HTTPException)
async def handle_http_exception(request, exc):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

# より具体的なハンドラ
@app.exception_handler(NotFoundException)
async def handle_not_found(request, exc):
    return JSONResponse({"error": "Not found", "path": request.path}, status_code=404)

# NotFoundException が発生した場合:
#   → handle_not_found が呼ばれる (より具体的)
# BadRequestException が発生した場合:
#   → handle_http_exception が呼ばれる (親クラスのハンドラにフォールバック)
```

## デフォルトのエラーレスポンス

Pykour はデフォルトで以下の例外ハンドラを登録しています:

- `HTTPException` - HTTP エラーレスポンスを返す
- `ValidationError` - 422 ステータスでバリデーションエラーの詳細を返す

### HTTPException のデフォルトレスポンス

```json
{
    "detail": "Not Found"
}
```

### ValidationError のデフォルトレスポンス

```json
{
    "error": "Validation Error",
    "detail": [
        {
            "loc": ["body", "email"],
            "msg": "Invalid email format",
            "type": "value_error",
            "input": "invalid"
        }
    ]
}
```

## ExceptionHandler / ExceptionHandlerRegistry

Pykour は内部的に `ExceptionHandlerRegistry` を使って例外ハンドラを管理しています。上級ユーザーはこれらを直接使用することもできます。

```python
from pykour import ExceptionHandler, ExceptionHandlerRegistry
```

`ExceptionHandler` は型エイリアスで、`Callable[[Request, Any], Response | Awaitable[Response]]` を表します。

`ExceptionHandlerRegistry` は例外クラスとハンドラのマッピングを管理するクラスです:

```python
registry = ExceptionHandlerRegistry()
registry.add(NotFoundException, handle_not_found)

# 例外インスタンスから最適なハンドラを取得 (MRO に基づく)
handler = registry.get(exc)
```

通常は `@app.exception_handler` や `app.add_exception_handler` を使用すれば十分です。

## See also

- [Schema Validation](schema-validation.md) - ValidationError の詳細
- [Response](response.md) - レスポンスクラス
