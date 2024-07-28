# Middleware

Middleware is a function that operates between a request and a response. Middleware receives the request object, 
response object, and a reference to the next middleware function.
It can call the next middleware function or return a response.

## Usage

Middleware can be added using the `add_middleware()` method of the `Pykour` class.

```python
from pykour import Pykour
from pykour.middleware import GZipMiddleware

app = Pykour()
app.add_middleware(GZipMiddleware)
```

To add middleware that takes arguments, pass the arguments to the `add_middleware()` method.

```python
from pykour import Pykour
from pykour.middleware import UUIDMiddleware

app = Pykour()
app.add_middleware(UUIDMiddleware, header_name='X-Custom-ID')
```
