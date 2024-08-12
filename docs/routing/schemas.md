# Schema

The request body is mapped to a dictionary, but you can use a schema to take advantage of type hints.

## Defining a Schema

Schemas are defined by inheriting from `BaseSchema`.

```python
from pykour.schema import BaseSchema

class UserSchema(BaseSchema):
    name: str
    age: int
```

There is no need to define an `__init__` method for the schema.

## Using a Schema

To use a schema, specify the schema as an argument in methods that receive a request body, such as a POST method.

```python
from pykour import Pykour

from .schemas import UserSchema

app = Pykour()

@app.post('/users')
def create_user(user: UserSchema):
    return user
```

If the request body is

```json
{
    "name": "Alice",
    "age": 20
}
```

then user.name will return "Alice" and user.age will return 20.
