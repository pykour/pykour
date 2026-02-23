---
title: Schema Validation
parent: Core
nav_order: 5
---

# Schema Validation

Pykour は独自のスキーマバリデーションシステムを提供しています。`Schema` クラスを継承してリクエストデータのバリデーションルールを定義します。

```python
from pykour import Schema, Field
from pykour.schema import field_validator, model_validator
```

## Schema クラス

`Schema` を継承してバリデーション付きのデータモデルを定義します。インスタンス化時にバリデーションが自動実行されます。

```python
from pykour import Schema, Field

class UserSchema(Schema):
    name: str
    email: str
    age: int = Field(ge=0, le=150)
    role: str = "user"  # デフォルト値

# バリデーション成功
user = UserSchema(name="Alice", email="alice@example.com", age=30)
print(user.name)    # "Alice"
print(user.role)    # "user"

# バリデーション失敗 → ValidationError
user = UserSchema(name="Alice", email="alice@example.com", age=-1)
```

### model_dump()

スキーマインスタンスを辞書に変換します:

```python
user = UserSchema(name="Alice", email="alice@example.com", age=30)
data = user.model_dump()
# {"name": "Alice", "email": "alice@example.com", "age": 30, "role": "user"}
```

## Field()

フィールドにバリデーション制約やメタデータを設定します。

```python
Field(
    default=MISSING,
    *,
    default_factory=None,
    alias=None,
    ge=None,
    le=None,
    gt=None,
    lt=None,
    min_length=None,
    max_length=None,
    pattern=None,
    description=None,
)
```

### バリデーション制約

| パラメータ | 型 | 説明 | 対象の型 |
|-----------|-----|------|---------|
| `ge` | `int \| float` | 以上 (>=) | 数値 |
| `le` | `int \| float` | 以下 (<=) | 数値 |
| `gt` | `int \| float` | より大きい (>) | 数値 |
| `lt` | `int \| float` | より小さい (<) | 数値 |
| `min_length` | `int` | 最小長 | 文字列 |
| `max_length` | `int` | 最大長 | 文字列 |
| `pattern` | `str` | 正規表現パターン | 文字列 |

### その他のオプション

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `default` | `Any` | デフォルト値 |
| `default_factory` | `Callable` | デフォルト値のファクトリ関数 |
| `alias` | `str` | JSON キーのエイリアス |
| `description` | `str` | OpenAPI ドキュメント用の説明 |

`default` と `default_factory` は同時に指定できません。

### 使用例

```python
class ProductSchema(Schema):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    quantity: int = Field(ge=0, le=10000)
    sku: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")
    tags: list[str] = Field(default_factory=list)
    description: str = Field(default="", description="Product description")
```

## field_validator

特定のフィールドに対するカスタムバリデーションロジックを定義します。

```python
field_validator(
    *fields: str,
    mode: Literal["before", "after"] = "after",
    check_fields: bool = True,
)
```

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `*fields` | `str` | (必須) | バリデーション対象のフィールド名 |
| `mode` | `"before" \| "after"` | `"after"` | 実行タイミング |
| `check_fields` | `bool` | `True` | フィールド存在チェック |

### mode の違い

- `"before"` - 型変換の前に実行される (生の入力値を受け取る)
- `"after"` - 型変換の後に実行される (変換済みの値を受け取る)

```python
class UserSchema(Schema):
    name: str
    email: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()
```

### before モードの例

```python
class ItemSchema(Schema):
    price: float

    @field_validator("price", mode="before")
    @classmethod
    def parse_price(cls, v: Any) -> Any:
        if isinstance(v, str) and v.startswith("$"):
            return v[1:]  # "$9.99" → "9.99"
        return v
```

## model_validator

モデル全体に対するバリデーションを定義します。フィールド間の関連性チェックに使用します。

```python
model_validator(
    *,
    mode: Literal["before", "after"] = "after",
)
```

### after モード (デフォルト)

バリデーション済みのモデルインスタンスを受け取ります:

```python
class PasswordSchema(Schema):
    password: str = Field(min_length=8)
    password_confirm: str

    @model_validator(mode="after")
    @classmethod
    def passwords_match(cls, model: "PasswordSchema") -> "PasswordSchema":
        if model.password != model.password_confirm:
            raise ValueError("Passwords do not match")
        return model
```

### before モード

生の入力データ (dict) を受け取ります。データの前処理に使用します:

```python
class SignupSchema(Schema):
    username: str
    email: str

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, data: dict) -> dict:
        if "username" in data:
            data["username"] = data["username"].lower()
        return data
```

## ValidationError

バリデーション失敗時に送出される例外です。

```python
from pykour import ValidationError
from pykour.schema.errors import ErrorDetail
```

### エラーレスポンスの形式

`ValidationError.to_dict()` は以下の形式の辞書を返します:

```json
{
    "error": "Validation Error",
    "detail": [
        {
            "loc": ["age"],
            "msg": "Value must be >= 0",
            "type": "value_error",
            "input": -1,
            "ctx": {"ge": 0}
        }
    ]
}
```

### ErrorDetail

各バリデーションエラーの詳細情報です:

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `loc` | `tuple[str \| int, ...]` | エラー位置 (フィールド名のパス) |
| `msg` | `str` | エラーメッセージ |
| `type` | `str` | エラータイプ |
| `input` | `Any` | 入力値 |
| `ctx` | `dict \| None` | コンテキスト情報 (制約値など) |

### エラーハンドリング

```python
from pykour import ValidationError

try:
    user = UserSchema(name="", email="invalid", age=-1)
except ValidationError as e:
    print(e.to_dict())
    for error in e.errors:
        print(f"{error.loc}: {error.msg}")
```

## ハンドラでの使用

`Body()` マーカーと組み合わせて、リクエストボディを自動バリデーションします:

```python
from pykour import Schema, Field, Body
from pykour.schema import field_validator

class CreateUserSchema(Schema):
    name: str = Field(min_length=1, max_length=50)
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()

async def post(
    request: Request,
    data: CreateUserSchema = Body(),
) -> JSONResponse:
    # data は自動的にバリデーション済み
    return JSONResponse(data.model_dump(), status_code=201)
```

バリデーション失敗時は自動的に 422 Unprocessable Entity レスポンスが返されます。

## See also

- [Parameter Injection](parameter-injection.md) - Body() マーカーの詳細
- [Exception Handling](exception-handling.md) - バリデーションエラーのカスタマイズ
