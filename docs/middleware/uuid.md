# UUID Middleware

The UUID Middleware creates a UUID to uniquely identify requests and adds it to the request and response headers.

## Usage

```python
from pykour import Pykour
from pykour.middleware import UUIDMiddleware

app = Pykour()
app.add_middleware(UUIDMiddleware)

@app.get('/')
def index():
    return { 'message': 'Hello, World!' }
```

By default, the UUID Generation Middleware uses the `x-request-id` header.

## Using a Custom Header

If you want to use a header other than `x-request-id`, you can specify the header name using the `header_name` argument.

```python
from pykour import Pykour
from pykour.middleware import UUIDMiddleware

app = Pykour()
app.add_middleware(UUIDMiddleware, header_name="X-TEST-ID")

@app.get('/')
def index():
    return { 'message': 'Hello, World!' }
```
