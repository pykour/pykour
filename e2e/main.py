from pykour import Pykour, Config
from pykour.db import Connection

app = Pykour()
app.config = Config("./e2e/config.yaml")


@app.get("/")
def index(conn: Connection):
    return list(
        map(
            lambda user: {"username": user["username"], "email": user["email"]},
            conn.fetch_many("SELECT * FROM users"),
        )
    )
