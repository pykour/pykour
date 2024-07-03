# Pykour

[![Python Versions](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/pykour)](https://pypi.org/project/pykour/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pykour)](https://pypi.org/project/pykour/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/pykour/pykour/actions/workflows/ci.yml/badge.svg)](https://github.com/pykour/pykour/actions/workflows/ci.yml)

Pykour is a web application framework for Python, designed to quickly implement REST APIs.
Its usage is very similar to Flask and FastAPI, making it relatively easy to learn in a short period of time.

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
$ pykour run main:app
```

## License

This project is licensed under the terms of the MIT license.
