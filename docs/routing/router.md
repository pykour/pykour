# Routing

Routing in Pykour is defined using the Router class.

## Routing with the `route()` Decorator

The simplest way to define routes is to use the `route()` decorator of the Pykour class.

The `route()` decorator uses the `GET` method by default. To use other HTTP methods, 
you can explicitly specify them using the method argument.

### Using Decorators Corresponding to HTTP Methods

Pykour provides decorators corresponding to HTTP methods:

- `get()`
- `post()`
- `put()`
- `delete()`
- `patch()`
- `options()`
- `head()`

These decorators are shortcuts for the `route()` decorator.

### Custom HTTP Methods

Pykour does not support custom HTTP methods. Additionally, the TRACE method is not supported for security reasons.

## Routing Configuration with Router

You can modularize your routing configuration using the Router class.

## Hierarchical Routing with Router

You can create hierarchical routing using the Router class.
