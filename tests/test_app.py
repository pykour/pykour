def test_init():
    from pykour.app import ASGIApp

    app = ASGIApp()

    assert app is not None
