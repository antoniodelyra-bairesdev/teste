# from .authentication import auth_router, logout_router
from .logout import router as logout_router
from .password_reset_confirm import router as password_reset_confirm_router
from .registration import router as registration_router
from .root import router as root_router
from .token import router as token_router
from .password import router as password_router, public_router as password_public_router


# from .password import router as password_router


__all__ = [
    # "auth_router",
    "logout_router",
    "password_reset_confirm_router",
    "registration_router",
    "password_router",
    "password_public_router",
    "root_router",
    "token_router",
]
