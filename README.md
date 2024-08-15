[![Pykour](https://pykour.com/assets/pykour.png)](https://pykour.com)

[![Python Versions](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/pykour)](https://pypi.org/project/pykour/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pykour)](https://pypi.org/project/pykour/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/pykour/pykour/actions/workflows/ci.yml/badge.svg)](https://github.com/pykour/pykour/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pykour/pykour/graph/badge.svg?token=VJR4NSJ5FZ)](https://codecov.io/gh/pykour/pykour)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/1195c94493854e9fb06fb8c3844e36ef)](https://app.codacy.com/gh/pykour/pykour/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

**Documentation**: https://pykour.com  
**Source Code**: https://github.com/pykour/pykour

## Features

Pykour is a modern, fast, and easy to use REST framework for Python.

It provides an interface very similar to Flask and FastAPI, allowing those familiar with these frameworks
to learn it in a short period.

- REST API Specialized: Pykour is a web application framework specifically designed for building REST API servers.
- Fast: Pykour is engineered to operate at high speeds.
- Easy: With an interface similar to Flask and FastAPI, Pykour is designed for quick use and learning. 
  The documentation is also concise, enabling rapid reading.
- Robust: Pykour is a highly robust and reliable framework, achieving high test coverage.
- Support testing: Pykour provides a testing client to test your application.

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

## Maintainers

The original author of Pykour is [Takashi Yamashina](mailto:takashi.yamashina@gmail.com).

## License

This project is licensed under the terms of the [MIT license](https://raw.githubusercontent.com/pykour/pykour/main/LICENSE).
