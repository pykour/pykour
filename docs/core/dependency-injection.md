# Dependency Injection

Pykour は組み込みの依存性注入 (DI) コンテナを提供しています。サービスの登録、スコープ管理、ハンドラへの自動注入をサポートします。

```python
from pykour.di import ServiceContainer, Depends, Scope
```

## ServiceContainer

サービスの登録と解決を管理するコンテナです。

```python
container = ServiceContainer()
```

### register()

クラスをサービスとして登録します。

```python
container.register(
    interface: type,
    implementation: type | None = None,
    *,
    scope: Scope = Scope.TRANSIENT,
)
```

```python
# 自己登録 (interface = implementation)
container.register(UserService)

# インターフェースと実装の分離
container.register(IUserService, UserServiceImpl)

# スコープ指定
container.register(ConfigService, scope=Scope.SINGLETON)
container.register(RequestContext, scope=Scope.REQUEST)
```

### register_factory()

ファクトリ関数でサービスを生成します。同期・非同期の両方に対応しています。

```python
container.register_factory(
    interface: type,
    factory: Callable[..., T] | Callable[..., Awaitable[T]],
    *,
    scope: Scope = Scope.TRANSIENT,
)
```

```python
# 同期ファクトリ
container.register_factory(
    Database,
    lambda: Database.connect("postgresql://..."),
    scope=Scope.SINGLETON,
)

# 非同期ファクトリ
async def create_db() -> Database:
    return await Database.connect_async("postgresql://...")

container.register_factory(Database, create_db, scope=Scope.SINGLETON)
```

### register_instance()

事前に作成済みのインスタンスをシングルトンとして登録します。

```python
container.register_instance(interface: type, instance: T)
```

```python
config = Config(debug=True, db_url="sqlite:///app.db")
container.register_instance(Config, config)
```

## Scope

サービスのライフサイクルを定義するスコープです。

| スコープ | 説明 |
|---------|------|
| `Scope.SINGLETON` | アプリケーション全体で 1 つのインスタンスを共有 |
| `Scope.TRANSIENT` | 解決のたびに新しいインスタンスを生成 |
| `Scope.REQUEST` | リクエストごとに 1 つのインスタンスを共有 |

```python
from pykour.di import Scope

# シングルトン: アプリ全体で共有
container.register(CacheService, scope=Scope.SINGLETON)

# トランジェント: 毎回新規作成 (デフォルト)
container.register(UserService, scope=Scope.TRANSIENT)

# リクエストスコープ: リクエスト内で共有
container.register(RequestLogger, scope=Scope.REQUEST)
```

## Depends()

ハンドラの引数に `Depends()` マーカーを使用して、DI コンテナからサービスを注入します。

```python
Depends(dependency: type | Callable | None = None)
```

### 型ヒントによる自動解決

`Depends()` の引数を省略すると、パラメータの型ヒントに基づいて自動解決されます:

```python
from pykour.di import Depends

class UserRepository:
    def find(self, user_id: int):
        return {"id": user_id, "name": "Alice"}

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, user_id: int):
        return self.repo.find(user_id)

# コンテナにサービスを登録
container.register(UserRepository)
container.register(UserService)

# ハンドラで注入
async def get(
    request: Request,
    id: int = Path(),
    service: UserService = Depends(),
) -> JSONResponse:
    user = service.get_user(id)
    return JSONResponse(user)
```

### 明示的な依存指定

`Depends()` にクラスやファクトリ関数を渡して、注入するサービスを明示的に指定できます:

```python
def get_db_connection():
    return Database("postgresql://...")

async def get(
    request: Request,
    db = Depends(get_db_connection),
) -> JSONResponse:
    return JSONResponse({"status": "ok"})
```

## resolve / aresolve

コンテナから手動でサービスを解決します。

```python
# 同期解決
user_service = container.resolve(UserService)

# 非同期解決 (async ファクトリの場合に必要)
db = await container.aresolve(Database)

# 解決できない場合に None を返す
service = container.resolve_or_none(OptionalService)
```

## RequestScope

リクエストスコープのサービスは `RequestScope` コンテキストマネージャ内で解決されます。Pykour は内部的に各リクエストでこれを使用しています。

```python
from pykour.di import RequestScope

async with RequestScope():
    # このブロック内で解決された REQUEST スコープのサービスは
    # 同じインスタンスが再利用される
    service1 = container.resolve(RequestLogger)
    service2 = container.resolve(RequestLogger)
    assert service1 is service2  # True
```

## 完全な例

```python
from pykour import Pykour, Path, JSONResponse
from pykour.di import ServiceContainer, Depends, Scope

# サービス定義
class DatabasePool:
    async def query(self, sql: str):
        return [{"id": 1}]

class UserRepository:
    def __init__(self, db: DatabasePool):
        self.db = db

    async def find_by_id(self, user_id: int):
        rows = await self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        return rows[0] if rows else None

class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    async def get_user(self, user_id: int):
        return await self.repo.find_by_id(user_id)

# アプリケーション設定
app = Pykour()

# DI 設定
app.services.register(DatabasePool, scope=Scope.SINGLETON)
app.services.register(UserRepository)
app.services.register(UserService)
```

```python
# routes/users/[id]/route.py
async def get(
    request: Request,
    id: int = Path(),
    service: UserService = Depends(),
) -> JSONResponse:
    user = await service.get_user(id)
    if user is None:
        raise NotFoundException(f"User {id} not found")
    return JSONResponse(user)
```

## See also

- [Parameter Injection](parameter-injection.md) - Depends() マーカーの概要
- [Schema Validation](schema-validation.md) - リクエストデータのバリデーション
