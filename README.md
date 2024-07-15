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

## This version is a beta version

This version is for evaluation purposes only and is not recommended for production use. Please note the following points
for the beta version:

- Features may be incomplete.
- Bugs and unexpected behavior may be present.
- APIs and internal structures may change in future versions.

## Features

Pykour is a web application framework for Python designed to quickly implement REST APIs. It provides an interface very 
similar to Flask and FastAPI, allowing those familiar with these frameworks to learn it in a short period.

- REST API Specialized: Pykour is a web application framework specifically designed for building REST API servers.
- Fast: Pykour is engineered to operate at high speeds.
- Easy: With an interface similar to Flask and FastAPI, Pykour is designed for quick use and learning. The documentation is also concise, enabling rapid reading.
- Robust: Pykour is a highly robust and reliable framework, achieving high test coverage.

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
