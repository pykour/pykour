## Middleware

Pykour can use middleware to modify requests and responses. Middleware executes before the request is passed to the route handler.

```python
from pykour import Pykour
from pykour.middleware import gzip_middleware

app = Pykour()

app.add_middleware(gzip_middleware())

```

### Gzip Middleware

The `gzip_middleware` compresses the response in gzip format. To enable gzip compression, 
add `gzip_middleware` as middleware.

```python
from pykour import Pykour
from pykour.middleware import gzip_middleware

app = Pykour()

app.add_middleware(gzip_middleware)
```

`gzip_middleware` compresses only responses larger than the size specified by `minimum_size`. The default `minimum_size` 
is `1024` bytes.

```python
from pykour import Pykour
from pykour.middleware import gzip_middleware

app = Pykour()

app.add_middleware(gzip_middleware(minimum_size=512))
```

In this example, only responses of `512` bytes or larger will be GZIP compressed.

### UUID Middleware

The `uuid_middleware` adds a UUID to the request. By default, it is added to the `X-Request-ID` header.

```python
from pykour import Pykour
from pykour.middleware import uuid_middleware

app = Pykour()

app.add_middleware(uuid_middleware)
```

The `uuid_middleware` can specify the header name to add using the `header_name` argument.

```python
from pykour import Pykour
from pykour.middleware import uuid_middleware

app = Pykour()

app.add_middleware(uuid_middleware(header_name="X-My-Request-ID"))
```
