from pykour import Router
from .user import router as user_router

router = Router()
router.add_router(user_router, "/user")
