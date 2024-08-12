# Routing

Routing is the method of associating application URLs with route functions.
In Pykour, routes are defined using the `route()` decorator.

```python
from pykour import Pykour

app = Pykour()

@app.route('/')
async def index():
    return {'message': 'Hello, World!'}
```
