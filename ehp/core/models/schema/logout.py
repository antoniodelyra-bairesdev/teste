from pydantic import BaseModel, Field
from starlette import status


class LogoutResponse(BaseModel):
    """
    Response model for a successful logout.
    """

    message: str = Field(..., examples=["Logged out successfully"])
    status_code: int = Field(default=status.HTTP_200_OK, examples=[200])
