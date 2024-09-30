from pykour import Pykour, Config


from .router import router

app = Pykour()
app.config = Config("./e2e/config.yaml")

app.add_router(router, "/api/v1")
