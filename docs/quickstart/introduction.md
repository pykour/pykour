# Quickstart

Let’s learn the basics of using Pykour. Follow the [Installation](../installation.md) for project setup and Pykour installation.

## Hello, World!

A minimal Pykour application looks like this:

```python
from pykour import Pykour

app = Pykour()

@app.route('/')
def hello():
    return { "message": "Hello, Pykour!" }
```

What is this code doing?

1.	First, it imports the `Pykour` class from the `pykour` module.
2.	Next, it creates an instance of the `Pykour` class and assigns it to the app variable.
3.	It defines the `/` route using the route() decorator.
4.	The `hello()` function returns a dictionary with a single key-value pair.

Save this code with a name like `main.py`.

To run the application, you need to tell the `pykour` command where your application is located by specifying `main:app`.

```bash
$ pykour dev main:app
```

Open your browser and go to [http://localhost:8000/](http://localhost:8000/). You should see the text `{"message": "Hello, Pykour"}`.
