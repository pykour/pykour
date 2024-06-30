# Pykour

Pykour is modern, fast, and easy to use web framework for Python.

The key features are:

- **Fast**: High performance. One of the fastest Python frameworks available.
- **Easy to learn**: Designed to be easy to use and learn. Less time reading docs.
- **Robust**: Get production-ready code.

## Project layout

    mkdocs.yml    # The configuration file.
    docs/
        index.md  # The documentation homepage.
        ...       # Other markdown pages, images and other files.

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
