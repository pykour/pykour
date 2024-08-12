# Testing

Pykourでは、テストを支援するツールを提供しています。

## ルートのテスト

`pykour.testing`モジュールは、Pykourのテストを行うためのツールを提供しています。

```python
import pytest
from pykour.testing import perform, get

@pytest.mark.asyncio
async def test_hello():
    from main import app
    
    response = await perform(app, get('/hello'))
    response.is_ok().expect({ 'message': 'Hello, World!' })
```

`perform`関数は、あなたのアプリケーションとリクエストを受け取り、レスポンスを返します。
`is_ok`メソッドは、レスポンスが成功したかどうかを確認し、`expect`メソッドは、レスポンスの内容を確認します。

リクエストは、`get`、`post`、`put`、`delete`、`patch`、`options`、`head`関数を使用して作成できます。