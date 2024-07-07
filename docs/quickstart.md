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

To run the application, use the pykour command or python -m pykour. You need to tell Pykour where your application is 
located using `main:app`.

```bash
$ pykour run main:app
```

Now, open your browser and go to `http://localhost:8000/`. You should see the message "Hello, World!".

## Routing

Pykour uses the `route()` decorator to define routes. The decorator takes a single argument, the URL path.

```python
@app.route('/')
def index():
    return { "message": "Index Page" }

@app.route('/hello')
def hello():
    return { "message": "Hello, Pykour!" }
```

The `route()` method defines a route with the `GET` method. You can also specify the HTTP methods explicitly.

```python
@app.route('/hello', method='POST')
def post_hello():
    return { "message": "Hello, Pykour!" }
```

## Variables in Routes

You can also use variables within a route. 

```python
@app.route('/hello/{name}')
def hello_name(name):
    return { "message": f"Hello, {name}!" }
```

`{name}` or `:name` is mapped to the argument `name`. By default, it is mapped with type str, but it can also be mapped 
to int or float, depending on the type hint.

```python
@app.route('/users/:age')
def user_age(age: int):
    return { "message": f"User age is {age}" }
```

## HTTP Methods

Web applications use different HTTP methods when accessing URLs. You should familiarize yourself with the HTTP methods 
as you work with Pykour.

```python
@app.route('/hello', method='POST')
def post_hello():
    return { "message": "Hello, Pykour!" }
```

You can also use the `get()`, `post()`, `put()`, `delete()`, `patch()`, `options()`, `head()` and `trace()` decorators,
which are shortcuts for the `route()` decorator.


```python
@app.get('/')
def get():
    ...

@app.post('/')
def post():
    ...

@app.put('/')
def put():
    ...

@app.delete('/')
def delete():
    ...

@app.patch('/')
def patch():
    ...
```

If you want to support `OPTIONS`, `HEAD`, and `TRACE` method, you can use the `options()`, `head()` , and `trace()` decorator. Pykour does the processing to respond to
the OPTIONS method response, so it only needs to declare an empty method.

```python
@app.options('/')
def options():
    ...

@app.head('/')
def head():
    ...

@app.trace('/')
def trace():
    ...
```
