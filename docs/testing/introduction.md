# Testing

Pykour provides tools to assist in testing.

## Testing the route handler

The `pykour.testing` module provides tools to help you test Pykour.

```python
import pytest
from pykour.testing import perform, get

@pytest.mark.asyncio
async def test_hello():
    from main import app
    
    response = await perform(app, get('/hello'))
    response.is_ok().expect({ 'message': 'Hello, World!' })
```

The `perform` function takes your application and request and returns a response.
The `is_ok` method checks if the response was successful, and the `expect` method checks the content of the response.

Requests can be made using the `get`, `post`, `put`, `delete`, `patch`, `options`, and `head` functions.
