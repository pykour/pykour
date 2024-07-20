# Quickstart

Let’s learn the basics of using Pykour. Follow the [Installation](installation.md) for project setup and Pykour installation.

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

## Routing

In Pykour, routes are defined using the `route()` decorator, which takes a URL path.

```python
@app.route('/')
def index():
    return { "message": "Index Page" }

@app.route('/hello')
def hello():
    return { "message": "Hello, Pykour!" }
```

By default, the `route()` decorator defines routes with the `GET` method. If you want to use HTTP methods other than 
`GET`, you can explicitly specify the HTTP method.

```python
@app.route('/hello', method="POST")
def post_hello():
    return { "message": "Hello, Pykour!" }
```

The `route()` decorator also defines routes with a default status code of `200 OK`.
If you want to change the status code, you can specify it using the `status_code` argument.

```python
@app.route('/hello', method="POST", status_code=201)
def post_hello():
    return { "message": "Hello, Pykour!" }
```

## Variables in Routes

You can also use variables within the route path.

```python
@app.route('/hello/{name}')
def hello_name(name):
    return { "message": f"Hello, {name}!" }
```

`{name}` or `:name` maps to the name argument. 
By default, it maps to the str type, but it can also map to `int` or `float` based on the type hint.

```python
@app.route('/users/:age')
def user_age(age: int):
    return { "message": f"User age is {age}" }
```

When receiving data with `POST` or `PUT` methods, you can accept data as a dictionary.

```python
@app.route('/users', method="POST")
def create_user(data: dict):
    return { 'message': 'User created', 'name': data['name'] }
```

Additionally, you can receive data using a schema.

```python
from pykour.schema import BaseSchema

class UserSchema(BaseSchema):
    name: str
    age: int


@app.route('/users', method="POST")
def create_user(data: UserSchema):
    return { 'message': 'User created', 'name': data.name }
```

## HTTP Methods

In a REST API, different HTTP methods are used. Pykour provides decorators corresponding to each HTTP method.

The `get()`, `post()`, `put()`, `delete()`, and `patch()` decorators are shortcuts for the `route()` decorator.

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

If you want to support the `OPTIONS` and `HEAD` methods, you can use the `options()` and `head()` decorators. 
Pykour handles the response for the `OPTIONS` and `HEAD` methods, so you only need to declare an empty method.

```python
@app.options('/')
def options():
    ...

@app.head('/')
def head():
    ...
```

The `TRACE` method is not supported for security reasons.

Methods other than `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, and `HEAD` cannot be set with the `route()` 
decorator, and shortcut decorators are not provided. If an unsupported HTTP method is accessed, 
Pykour will return a `404 Not Found` status code.

## Schema

In Pykour, you can use schemas to receive request data. A schema is a class that defines the structure of the data.

```python
from pykour.schema import BaseSchema

class UserSchema(BaseSchema):
    name: str
    age: int

@app.route('/users', method="POST")
def create_user(data: UserSchema):
    return { 'message': 'User created', 'name': data.name }

```

The `BaseSchema` class is the base class for defining schemas. When defining a schema, inherit from the `BaseSchema` class.

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
