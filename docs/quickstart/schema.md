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
