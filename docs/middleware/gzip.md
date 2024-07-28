# GZIP Middleware

The GZIP Middleware compresses the response body using GZIP compression.

## Usage

```python
from pykour import Pykour
from pykour.middleware import GZipMiddleware

app = Pykour()
app.add_middleware(GZipMiddleware)
```

By default, the response body is not compressed if it is less than 500 bytes.

## Using a Custom Threshold

If you want to use a custom threshold other than 500 bytes,
you can specify the threshold using the `minimum_size` argument.

```python
from pykour import Pykour
from pykour.middleware import GZipMiddleware

app = Pykour()
app.add_middleware(GZipMiddleware, minimum_size=1024)
```
