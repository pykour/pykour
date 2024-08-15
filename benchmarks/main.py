from pykour import Pykour

app = Pykour()


@app.get("/")
def index():
    return {"message": "Hello, World!"}
