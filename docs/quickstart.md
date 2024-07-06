# Quickstart

This is a quickstart guide for the `myapp` application.

## Hello, World!

A minimal Pykour application looks like this:

```python
from pykour import Pykour

app = Pykour()

@app.route('/')
def hello_world():
    return { "message": "Hello, World!" }
```

So, what's happening here?

1. First we imported the `Pykour` class from the `pykour` module.
2. Next we create an instance of the `Pykour` class and assign it to the variable `app`.
3. We then use the route() decorator to define a route for the root URL `/`.
4. The `hello_world()` function returns a dictionary with a single key-value pair.

Save it as `main.py` or something similar.

To run the application, use the pykour command or python -m pykour. You need to tell the Pykour where you application is with the `main:py`.

```bash
$ pykour run main:app
```


