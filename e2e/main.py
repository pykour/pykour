from pykour import Pykour, Config

app = Pykour(config=Config("config.yaml"))


@app.get("/")
def hello():
    return {"message": "Hello, World!"}
