# UUID生成ミドルウェア

UUID生成ミドルウェアは、リクエストを一意に特定するUUIDを生成し、リクエストおよびレスポンスヘッダーに追加します。

## 使用方法

```python
from pykour import Pykour
from pykour.middleware import UUIDMiddleware

app = Pykour()
app.add_middleware(UUIDMiddleware) # UUID生成ミドルウェアを追加

@app.get('/')
def index():
    return { 'message': 'Hello, World!' }
```

デフォルトでは、UUID生成ミドルウェアは`x-request-id`ヘッダーを使用します。

## 任意のヘッダーを使用する

任意のヘッダーを使用する場合は、`header_name`引数を使用して指定できます。

```python
from pykour import Pykour
from pykour.middleware import UUIDMiddleware

app = Pykour()
app.add_middleware(UUIDMiddleware, header_name="X-TEST-ID") # UUID生成ミドルウェアを追加し、ヘッダー名を指定

@app.get('/')
def index():
    return { 'message': 'Hello, World!' }
```

分散トレーシングを使用している場合などで、特定のヘッダーが必要な場合は、この方法を使用してください。

## UUID生成ミドルウェアのシナリオ

UUID生成ミドルウェアを使用するシナリオには次の2つがあります。

- PykourがリクエストごとにUUIDを生成する
- クライアントから送信されたヘッダーを使用する

### PykourがリクエストごとにUUIDを生成する

リクエストヘッダーにヘッダーがない場合は、PykourがリクエストごとにUUIDを生成します。
リクエストごとにUUIDを生成したい場合は、この方法を使用してください。


### クライアントから送信されたヘッダーを使用する

クライアントから当該ヘッダーが送信された場合は、そのヘッダーをレスポンスヘッダーに追加します。
クライアントやアプリケーションサーバーの前にミドルウェアを使用している場合は、この方法を使用してください。