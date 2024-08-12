# Pykour

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

@app.route('/')
async def index():
    return {'message': 'Hello, World!'}
```

### Run the application

```bash
$ pykour dev main:app
```

## License

This project is licensed under the terms of the [MIT license](https://raw.githubusercontent.com/pykour/pykour/main/LICENSE).
