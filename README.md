# Pykour

[![Python Versions](https://img.shields.io/badge/Python-3.9%20|%203.10%20|%203.11%20|%203.12-blue)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/pykour)](https://pypi.org/project/pykour/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pykour)](https://pypi.org/project/pykour/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/pykour/pykour/actions/workflows/ci.yml/badge.svg)](https://github.com/pykour/pykour/actions/workflows/ci.yml)

Pykour is modern, fast, and easy to use web framework for Python.

The key features are:

- **Fast**: High performance. One of the fastest Python frameworks available.
- **Fewer bugs**: Reduce about 40% of human (developer) induced errors.
- **Easy to learn**: Designed to be easy to use and learn. Less time reading docs.
- **Robust**: Get production-ready code.

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
