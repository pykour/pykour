from pykour import Pykour, Config
from pykour.db import Connection

app = Pykour(config=Config("./e2e/config.yaml"))


@app.get("/")
def index(conn: Connection):
    return list(
        map(
            lambda user: {"username": user["username"], "email": user["email"]},
            conn.find_many("SELECT * FROM users"),
        )
    )
