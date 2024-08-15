from pykour import Pykour

app = Pykour()


@app.get("/")
async def index():
    return {"message": "Hello, World!"}
