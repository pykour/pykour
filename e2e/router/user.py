from pykour import Router
from pykour.db import Connection

router = Router()


@router.get("/")
async def index(conn: Connection):
    return list(
        map(
            lambda user: {"username": user["username"], "email": user["email"]},
            conn.fetch_many("SELECT * FROM users"),
        )
    )


@router.get("/{user_id}")
async def get(conn: Connection, user_id: int):
    user = conn.fetch_one("SELECT * FROM users WHERE id = ?", user_id)
    return {"username": user["username"], "email": user["email"]}


@router.post("/")
async def create(conn: Connection, body: dict):
    conn.execute("INSERT INTO users (username, email) VALUES (?, ?)", body["username"], body["email"])
    return {"status": "ok"}


@router.put("/{user_id}")
async def update(conn: Connection, user_id: int, body: dict):
    conn.execute("UPDATE users SET username = ?, email = ? WHERE id = ?", body["username"], body["email"], user_id)
    return {"status": "ok"}


@router.delete("/{user_id}")
async def delete(conn: Connection, user_id: int):
    conn.execute("DELETE FROM users WHERE id = ?", user_id)
