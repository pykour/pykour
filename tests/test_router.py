from pykour.router import Router, Node, Route


def test_route_creation():
    route = Route("/test", "GET", "handler")
    assert route.path == "/test"
    assert route.method == "GET"
    assert route.handler == "handler"


def test_node_creation():
    node = Node("part")
    assert node.part == "part"
    assert node.children == []
    assert node.is_wild is False
    assert node.route_map == {}


def test_node_insertion():
    router = Router()
    router.add_route("/test", "GET", "handler")
    route = router.get_route("/test", "GET")
    assert route.path == "/test"
    assert route.method == "GET"
    assert route.handler == "handler"


def test_node_search_non_existent_route():
    router = Router()
    route = router.get_route("/nonexistent", "GET")
    assert route is None


def test_node_insertion_with_wildcard():
    router = Router()
    router.add_route("/test/:id", "GET", "handler")
    route = router.get_route("/test/123", "GET")
    assert route.path == "/test/:id"
    assert route.method == "GET"
    assert route.handler == "handler"


def test_node_search_with_wildcard_non_existent_route():
    router = Router()
    router.add_route("/test/:id", "GET", "handler")
    route = router.get_route("/test/nonexistent/123", "GET")
    assert route is None


def test_get_method():
    router = Router()

    @router.get("/test")
    def handler(): ...

    route = router.get_route("/test", "GET")
    assert route.path == "/test"
    assert router.exists("/test", "GET")


def test_post_method():
    router = Router()

    @router.post("/test")
    def handler(): ...

    route = router.get_route("/test", "POST")
    assert route.path == "/test"
    assert router.exists("/test", "POST")


def test_put_method():
    router = Router()

    @router.put("/test")
    def handler(): ...

    route = router.get_route("/test", "PUT")
    assert route.path == "/test"
    assert router.exists("/test", "PUT")


def test_delete_method():
    router = Router()

    @router.delete("/test")
    def handler(): ...

    route = router.get_route("/test", "DELETE")
    assert route.path == "/test"
    assert router.exists("/test", "DELETE")


def test_patch_method():
    router = Router()

    @router.patch("/test")
    def handler(): ...

    route = router.get_route("/test", "PATCH")
    assert route.path == "/test"
    assert router.exists("/test", "PATCH")


def test_options_method():
    router = Router()

    @router.options("/test")
    def handler(): ...

    route = router.get_route("/test", "OPTIONS")
    assert route.path == "/test"
    assert router.exists("/test", "OPTIONS")


def test_head_method():
    router = Router()

    @router.head("/test")
    def handler(): ...

    route = router.get_route("/test", "HEAD")
    assert route.path == "/test"
    assert router.exists("/test", "HEAD")


def test_trace_method():
    router = Router()

    @router.trace("/test")
    def handler(): ...

    route = router.get_route("/test", "TRACE")
    assert route.path == "/test"
    assert router.exists("/test", "TRACE")


def test_string_representation():
    router = Router()

    @router.get("/test")
    def handler(): ...

    assert str(router) == "GET /test -> handler()"
    assert repr(router) == "Router(prefix='')"
