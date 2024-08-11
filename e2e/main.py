from pykour import Pykour

app = Pykour()


@app.get("/")
def hello():
    return {"message": "Hello, World!"}
