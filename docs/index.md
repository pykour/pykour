# Pykour

PykourはPython向けのWebアプリケーションフレームワークで、REST APIを素早く実装することを目的としています。FlaskやFastAPIに非常に似た
インターフェースを提供しており、これらのフレームワークを習得している人にとっては短期間で学習することができます。

## Features

PykourはREST APIサーバーを構築することに特化したWebアプリケーションフレームワークです。

Pykourはリクエストとレスポンスを効率的に処理し、高いパフォーマンスを実現するように設計されています、 アプリケーションをスムーズかつ迅速に
実行できるように設計されています。

- **Fast**: Pykourは非常に高速に動作するように設計されています。
- **Easy**: PykourはFlaskやFastAPIに似たインターフェースを持ち、短時間で使用および学習できるように設計されています。ドキュメントも短時間で読めるようにしています。
  - **Robust**: Pykourは非常に堅牢で信頼性が高いフレームワークです。高いテストカバレッジを達成しています。

## Requirements

- Python 3.9+

## Installation

```bash
pip install pykour
```

## Example

### Create an application

```python
from pykour import Pykour

app = Pykour()

@app.route('/')
async def index():
    return {'message': 'Hello, World!'}
```

### Run the application

```bash
$ pykour dev main:app
```

## License

This project is licensed under the terms of the MIT license.
