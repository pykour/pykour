[![Pykour](https://pykour.com/assets/pykour.png)](https://pykour.com)

[![Python Versions](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/pykour)](https://pypi.org/project/pykour/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pykour)](https://pypi.org/project/pykour/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/pykour/pykour/actions/workflows/ci.yml/badge.svg)](https://github.com/pykour/pykour/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pykour/pykour/graph/badge.svg?token=VJR4NSJ5FZ)](https://codecov.io/gh/pykour/pykour)

**Documentation**: https://pykour.com  
**Source Code**: https://github.com/pykour/pykour

## Features

Pykour is a web application framework for Python, designed to quickly implement REST APIs.
Its usage is very similar to Flask and FastAPI, making it relatively easy to learn in a short period of time.

PykourはPython向けのWebアプリケーションフレームワークで、REST APIを素早く実装することを目的としています。
FlaskやFastAPIに非常に似たインターフェースを提供しており、これらのフレームワークを習得している人にとっては短期間で学習することができます。

- **REST API Specialized**: PykourはREST APIサーバーを構築することに特化したWebアプリケーションフレームワークです。
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

@app.get('/')
async def index():
    return {'message': 'Hello, World!'}
```

### Run the application

```bash
$ pykour dev main:app
```

## License

This project is licensed under the terms of the MIT license.
