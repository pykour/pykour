# スキーマ

リクエストボディは辞書型にマッピングされますが、型ヒントを活用するにはスキーマを使用する方法があります。

## スキーマの定義

スキーマはBaseSchemaを継承して定義します。

```python
from pykour.schema import BaseSchema

class UserSchema(BaseSchema):
    name: str
    age: int
```

