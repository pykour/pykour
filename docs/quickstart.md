# Quickstart

Pykourの基本的な使い方を学びましょう。プロジェクトのセットアップとPykourのインストールは[Installation](installation.md)に従ってください。

## Hello, World!

最小のPykourアプリケーションは次のようになります:

```python
from pykour import Pykour

app = Pykour()

@app.route('/')
def hello():
    return { "message": "Hello, Pykour!" }
```

このコードは何をしているのでしょうか？

1. 最初に`pykour`モジュールから`Pykour`クラスをインポートします。
2. 次に`Pykour`クラスのインスタンスを作成し、`app`変数に割り当てます。
3. `route()`デコレーターを使って`/`ルートを定義します。
4. `hello()`関数は、単一のキーとバリューのペアを持つ辞書を返します。

このコードを`main.py`などの名前で保存します。

アプリケーションを実行するには、`main:app`を指定して`pykour`コマンドにアプリケーションの場所を教える必要があります。

```bash
$ pykour dev main:app
```

ブラウザを開いて [http://localhost:8000/](http://localhost:8000/) に移動します。`{"message": "Hello, Pykour"}`というテキストが表示されるはずです。

## Routing

Pykour uses the `route()` decorator to define routes. The decorator takes a single argument, the URL path.

Pykourでは、`route()`デコレーターを使用してルートを定義します。デコレーターはURLパスを取ります。

```python
@app.route('/')
def index():
    return { "message": "Index Page" }

@app.route('/hello')
def hello():
    return { "message": "Hello, Pykour!" }
```

`route()`デコレーターは、デフォルトでは`GET`メソッドを持つルートを定義します。`GET`以外のHTTPメソッドを使用したい場合は、HTTPメソッドを明示的に
指定することもできます。

```python
@app.route('/hello', method="POST")
def post_hello():
    return { "message": "Hello, Pykour!" }
```

`route()`デコレーターは、デフォルトでは`200 OK`ステータスコードを持つルートを定義します。ステータスコードを変更したい場合は、
`status_code`引数を使用してステータスコードを指定できます。

```python
@app.route('/hello', method="POST", status_code=201)
def post_hello():
    return { "message": "Hello, Pykour!" }
```



## Variables in Routes

You can also use variables within a route. 
ルートパス内で変数を使用することもできます。

```python
@app.route('/hello/{name}')
def hello_name(name):
    return { "message": f"Hello, {name}!" }
```

`{name}` または `:name`は引数`name`にマップされます。デフォルトでは、str型にマップされますが、型ヒントに応じてintまたはfloatにマップする
こともできます。


```python
@app.route('/users/:age')
def user_age(age: int):
    return { "message": f"User age is {age}" }
```

`POST`メソッドや`PUT`メソッドでデータを受信する場合、辞書型でデータを受け取ったり、`BaseSchema`クラスのサブクラスを使用してデータを受け取る
ことができます。

```python
@app.route('/users', method="POST")
def create_user(data: dict):
    return { 'message': 'User created', 'name': data['name'] }
```


## HTTP Methods

REST APIでは異なるHTTPメソッドを使用します。Pykourでは、各HTTPメソッドに対応したデコレーターを提供しています。

`get()`, `post()`, `put()`, `delete()`, `patch()`デコレーターは、`route()`デコレーターの
ショートカットです。

```python
@app.get('/')
def get():
    ...

@app.post('/')
def post():
    ...

@app.put('/')
def put():
    ...

@app.delete('/')
def delete():
    ...

@app.patch('/')
def patch():
    ...
```

もし、`OPTIONS`, `HEAD`メソッドをサポートしたい場合は、`options()`, `head()`デコレーターを使用できます。
Pykourは`OPTIONS`メソッドのレスポンスを返すための処理を行うので、空のメソッドを宣言するだけでよいです。

```python
@app.options('/')
def options():
    ...

@app.head('/')
def head():
    ...
```

`TRACE`メソッドはセキュリティ上の理由からサポートされていません。

`GET`、`POST`、`PUT`、`DELETE`、`PATCH`、`OPTIONS`、`HEAD`メソッドを
以外のメソッドは`route()`デコレーターで設定できず、ショートカットデコレーターも提供していません。
サポートされていないHTTPメソッドでアクセスされた場合は、Pykourは`404 Not Found`ステータスコードを返します。
