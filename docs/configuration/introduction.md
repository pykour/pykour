# Configuration File

In Pykour, you can manage your application’s settings using a configuration file.
The configuration file is written in YAML format and defines the application’s settings.
Settings that begin with `pykour` are used by Pykour. If you create custom settings, use keys other than `pykour`.

## Usage

To use a configuration file, specify the path to the configuration file when creating a Pykour instance.

```python
from pykour import Pykour

app = Pykour('config.yaml')

@app.get('/')
def index():
    return { 'message': 'Hello, World!' }
```
