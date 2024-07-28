# Config

The Config class holds the contents of the configuration file.

## Using in Route Functions

You can retrieve the contents of the configuration file by receiving `config` as an argument in your route function.

```python
from pykour import Pykour, Config

app = Pykour('config.yaml')

@app.get('/')
def index(config: Config):
    return { 'message': config.get('message') }
```
