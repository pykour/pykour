# Pykour

Pykour is a web application framework for Python, designed to quickly implement REST APIs.
Its usage is very similar to Flask and FastAPI, making it relatively easy to learn in a short period of time.

## Features

Pykour is a web application framework specialized for building REST APIs.

It is designed to deliver high performance, ensuring efficient handling of requests and responses,
making your applications run smoothly and quickly.

One of the standout features of Pykour is its low learning curve.
Developers can master it in a short period of time, making it accessible even for those who are new to web development.
Pykour's structure and usage are similar to popular frameworks like Flask and FastAPI.
This familiarity allows developers to transition easily and leverage their existing knowledge,
speeding up the development process.

Whether you are building simple APIs or complex, data-driven applications,
Pykour provides the tools and flexibility you need to achieve your goals with ease and efficiency.

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
