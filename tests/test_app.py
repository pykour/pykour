def test_init():
    from pykour.app import ASGIApp

    app = ASGIApp()

    assert app._logger.name == "pykour"
