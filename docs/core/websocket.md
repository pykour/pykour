# WebSocket

Pykour は WebSocket によるリアルタイム双方向通信をサポートしています。ファイルベースルーティングと統合されており、`route.py` 内に `websocket` 関数を定義するだけで利用できます。

```python
from pykour import WebSocket, WebSocketDisconnect
```

## WebSocket ルートの定義

`route.py` に `websocket` という名前の非同期関数をエクスポートします:

```python
# routes/ws/route.py
from pykour import WebSocket

async def websocket(ws: WebSocket) -> None:
    await ws.accept()
    try:
        async for message in ws.iter_text():
            await ws.send_text(f"Echo: {message}")
    except Exception:
        pass
    finally:
        await ws.close()
```

HTTP ハンドラと WebSocket ハンドラは同じ `route.py` に共存できます:

```python
# routes/chat/route.py
from pykour import Request, HTMLResponse, WebSocket

async def get(request: Request) -> HTMLResponse:
    """チャットページの HTML を返す"""
    return HTMLResponse("<html>...</html>")

async def websocket(ws: WebSocket) -> None:
    """WebSocket 接続を処理"""
    await ws.accept()
    async for message in ws.iter_text():
        await ws.send_text(message)
```

## 接続ライフサイクル

WebSocket 接続は以下の状態を遷移します:

| 状態 | 値 | 説明 |
|------|-----|------|
| `CONNECTING` | 0 | 接続待機中 (初期状態) |
| `CONNECTED` | 1 | 接続確立済み |
| `DISCONNECTED` | 2 | 切断済み |

```
CONNECTING → accept() → CONNECTED → close() → DISCONNECTED
```

## 接続の受け入れ

```python
await ws.accept(
    subprotocol: str | None = None,
    headers: dict[str, str] | None = None,
)
```

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `subprotocol` | `str \| None` | サブプロトコル |
| `headers` | `dict \| None` | レスポンスヘッダー |

```python
async def websocket(ws: WebSocket) -> None:
    await ws.accept(subprotocol="chat")
    # ...
```

## メッセージの受信

### 個別受信

```python
# テキストメッセージ
text = await ws.receive_text()

# バイナリメッセージ
data = await ws.receive_bytes()

# JSON メッセージ
obj = await ws.receive_json()
```

### イテレータによる受信

ループでメッセージを連続受信する場合はイテレータを使用します:

```python
# テキストメッセージのイテレータ
async for message in ws.iter_text():
    print(message)

# バイナリメッセージのイテレータ
async for data in ws.iter_bytes():
    process(data)

# JSON メッセージのイテレータ
async for obj in ws.iter_json():
    handle(obj)
```

イテレータはクライアントが切断すると自動的に終了します (`WebSocketDisconnect` をキャッチして停止)。

## メッセージの送信

```python
# テキスト送信
await ws.send_text("Hello")

# バイナリ送信
await ws.send_bytes(b"\x00\x01\x02")

# JSON 送信
await ws.send_json({"type": "update", "data": [1, 2, 3]})
```

## 接続の切断

```python
await ws.close(code: int = 1000, reason: str = "")
```

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `code` | `int` | `1000` | WebSocket クローズコード |
| `reason` | `str` | `""` | 切断理由 |

## WebSocketDisconnect

クライアントが切断した場合にスローされる例外です:

```python
from pykour import WebSocket, WebSocketDisconnect

async def websocket(ws: WebSocket) -> None:
    await ws.accept()
    try:
        async for message in ws.iter_text():
            await ws.send_text(f"Echo: {message}")
    except WebSocketDisconnect as e:
        print(f"Client disconnected: code={e.code}, reason={e.reason}")
```

| 属性 | 型 | 説明 |
|------|-----|------|
| `code` | `int` | WebSocket クローズコード (デフォルト: 1000) |
| `reason` | `str` | 切断理由 |

## WebSocket プロパティ

`WebSocket` オブジェクトから接続情報にアクセスできます:

| プロパティ | 型 | 説明 |
|-----------|-----|------|
| `path` | `str` | リクエストパス |
| `path_params` | `dict[str, str]` | URL パスパラメータ |
| `query_params` | `dict[str, str \| list[str]]` | クエリパラメータ |
| `headers` | `dict[str, str]` | リクエストヘッダー |
| `state` | `WebSocketState` | 接続状態オブジェクト |
| `client` | `tuple \| None` | クライアントのアドレス情報 |
| `scope` | `Scope` | 生の ASGI スコープ |

## 動的セグメント付き WebSocket

パスパラメータを含む WebSocket ルートも使用できます:

```python
# routes/ws/[room_id]/route.py
from pykour import WebSocket

async def websocket(ws: WebSocket) -> None:
    room_id = ws.path_params["room_id"]
    await ws.accept()
    await ws.send_text(f"Joined room: {room_id}")

    async for message in ws.iter_text():
        await ws.send_text(f"[{room_id}] {message}")
```

## チャットアプリの例

```python
# routes/ws/chat/route.py
from pykour import WebSocket, WebSocketDisconnect

# 接続中のクライアントを管理
clients: set[WebSocket] = set()

async def websocket(ws: WebSocket) -> None:
    await ws.accept()
    clients.add(ws)
    try:
        async for message in ws.iter_text():
            # 全クライアントにブロードキャスト
            for client in clients:
                if client is not ws:
                    await client.send_text(message)
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)
```

## See also

- [File-Based Routing](routing.md) - WebSocket ルートの定義方法
- [Request](request.md) - HTTP リクエストの処理
