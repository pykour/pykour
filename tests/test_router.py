import pytest

from pykour.http import HttpMethod
from pykour.router import RouteRegistry, delete, get, head, options, patch, post, put, router


@pytest.mark.it("should define routes without a prefix")
def test_define_routes_without_prefix():

    @router()
    class UserRouter:

        @get("/users")
        def get_users():
            return "get_users"

        @post("/users")
        def post_users():
            return "post_users"

        @put("/users")
        def put_users():
            return "put_users"

        @patch("/users")
        def patch_users():
            return "patch_users"

        @delete("/users")
        def delete_users():
            return "delete_users"

        @options("/users")
        def options_users():
            return "options_users"

        @head("/users")
        def head_users():
            return "head_users"

    assert RouteRegistry.match(HttpMethod.GET, "/users") is not None
    assert RouteRegistry.match(HttpMethod.POST, "/users") is not None
    assert RouteRegistry.match(HttpMethod.PUT, "/users") is not None
    assert RouteRegistry.match(HttpMethod.PATCH, "/users") is not None
    assert RouteRegistry.match(HttpMethod.DELETE, "/users") is not None
    assert RouteRegistry.match(HttpMethod.OPTIONS, "/users") is not None
    assert RouteRegistry.match(HttpMethod.HEAD, "/users") is not None


@pytest.mark.it("should define routes with a prefix")
def test_define_routes_with_prefix():

    @router("/api/v1")
    class UserRouter:

        @get("/users")
        def get_users():
            return "get_users"

        @post("/users")
        def post_users():
            return "post_users"

        @put("/users")
        def put_users():
            return "put_users"

        @patch("/users")
        def patch_users():
            return "patch_users"

        @delete("/users")
        def delete_users():
            return "delete_users"

        @options("/users")
        def options_users():
            return "options_users"

        @head("/users")
        def head_users():
            return "head_users"

    assert RouteRegistry.match(HttpMethod.GET, "/api/v1/users") is not None
    assert RouteRegistry.match(HttpMethod.POST, "/api/v1/users") is not None
    assert RouteRegistry.match(HttpMethod.PUT, "/api/v1/users") is not None
    assert RouteRegistry.match(HttpMethod.PATCH, "/api/v1/users") is not None
    assert RouteRegistry.match(HttpMethod.DELETE, "/api/v1/users") is not None
    assert RouteRegistry.match(HttpMethod.OPTIONS, "/api/v1/users") is not None
    assert RouteRegistry.match(HttpMethod.HEAD, "/api/v1/users") is not None


def test_define_routes_using_multi_router_classes():

    @router("/api/v1")
    class UserRouter:

        @get("/users")
        def get_users():
            return "get_users"

    @router("/api/v1")
    class PostRouter:

        @get("/posts")
        def get_posts():
            return "get_posts"

    assert RouteRegistry.match(HttpMethod.GET, "/api/v1/users") is not None
    assert RouteRegistry.match(HttpMethod.GET, "/api/v1/posts") is not None


# def test_route_creation():
#     route = Route("/test", "GET", "handler")
#     assert route.path == "/test"
#     assert route.method == "GET"
#     assert route.handler == "handler"


# def test_node_creation():
#     node = Node("part")
#     assert node.part == "part"
#     assert node.children == []
#     assert node.is_wild is False
#     assert node.route is None


# def test_node_insertion():
#     router = Router()
#     router.add_route("/test", "GET", "handler")
#     route = router.get_route("/test", "GET")
#     assert route.path == "/test"
#     assert route.method == "GET"
#     assert route.handler == "handler"


# def test_node_search_non_existent_route():
#     router = Router()
#     route = router.get_route("/nonexistent", "GET")
#     assert route is None


# def test_node_insertion_with_wildcard():
#     router = Router()
#     router.add_route("/test/:id", "GET", "handler")
#     route = router.get_route("/test/123", "GET")
#     assert route.path == "/test/:id"
#     assert route.method == "GET"
#     assert route.handler == "handler"


# def test_node_search_with_wildcard_non_existent_route():
#     router = Router()
#     router.add_route("/test/:id", "GET", "handler")
#     route = router.get_route("/test/nonexistent/123", "GET")
#     assert route is None


# def test_get_method():
#     router = Router()

#     @router.get("/test")
#     def handler(): ...

#     route = router.get_route("/test", "GET")
#     assert route.path == "/test"
#     assert router.exists("/test", "GET")


# def test_post_method():
#     router = Router()

#     @router.post("/test")
#     def handler(): ...

#     route = router.get_route("/test", "POST")
#     assert route.path == "/test"
#     assert router.exists("/test", "POST")


# def test_put_method():
#     router = Router()

#     @router.put("/test")
#     def handler(): ...

#     route = router.get_route("/test", "PUT")
#     assert route.path == "/test"
#     assert router.exists("/test", "PUT")


# def test_delete_method():
#     router = Router()

#     @router.delete("/test")
#     def handler(): ...

#     route = router.get_route("/test", "DELETE")
#     assert route.path == "/test"
#     assert router.exists("/test", "DELETE")


# def test_patch_method():
#     router = Router()

#     @router.patch("/test")
#     def handler(): ...

#     route = router.get_route("/test", "PATCH")
#     assert route.path == "/test"
#     assert router.exists("/test", "PATCH")


# def test_options_method():
#     router = Router()

#     @router.options("/test")
#     def handler(): ...

#     route = router.get_route("/test", "OPTIONS")
#     assert route.path == "/test"
#     assert router.exists("/test", "OPTIONS")


# def test_head_method():
#     router = Router()

#     @router.head("/test")
#     def handler(): ...

#     route = router.get_route("/test", "HEAD")
#     assert route.path == "/test"
#     assert router.exists("/test", "HEAD")


# def test_trace_method():
#     router = Router()

#     with pytest.raises(ValueError):

#         @router.route("/test", method="TRACE")
#         def handler(): ...


# def test_string_representation():
#     router = Router()

#     @router.get("/test")
#     def handler(): ...

#     assert str(router) == "GET /test -> handler()"
#     assert repr(router) == "Router(prefix='')"


# def test_get_allowed_methods():
#     router = Router()

#     @router.get("/test")
#     def handler(): ...

#     methods = router.get_allowed_methods("/test")
#     assert methods == ["GET"]


# def test_add_router_without_prefix():
#     router = Router()
#     router2 = Router()

#     @router2.get("/test")
#     def handler(): ...

#     router.add_router(router2)
#     assert router.exists("/test", "GET")
#     assert router.get_allowed_methods("/test") == ["GET"]
#     assert str(router) == "GET /test -> handler()"
#     assert repr(router) == "Router(prefix='')"


# def test_add_router_with_prefix():
#     router = Router()
#     router2 = Router()

#     @router2.get("/test")
#     def handler(): ...

#     router.add_router(router2, prefix="/api")
#     assert router.exists("/api/test", "GET")
#     assert router.get_allowed_methods("/api/test") == ["GET"]
#     assert str(router) == "GET /api/test -> handler()"
#     assert repr(router) == "Router(prefix='')"


# def test_add_route_with_prefix():
#     router = Router(prefix="/api")

#     @router.get("/test")
#     def handler(): ...

#     assert router.exists("/api/test", "GET")
#     assert str(router) == "GET /api/test -> handler()"
#     assert repr(router) == "Router(prefix='/api')"
