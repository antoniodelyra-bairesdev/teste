from .logout import router as logout_router
from .registration import router as registration_router
from .root import router as root_router
from .token import router as token_router
from .password import router as password_router
from .wikiclip import router as wikiclip_router


__all__ = [
    "logout_router",
    "registration_router",
    "password_router",
    "root_router",
    "token_router",
    "wikiclip_router",
]
