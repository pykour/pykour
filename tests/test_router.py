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
