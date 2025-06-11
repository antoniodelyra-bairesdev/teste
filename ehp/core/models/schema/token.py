from pydantic import BaseModel


class TokenRequestData(BaseModel):
    """Request data model for OAuth 2.0 token endpoint"""

    username: str
    password: str
