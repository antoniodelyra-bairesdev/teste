from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic_core._pydantic_core import ValidationError

from ehp.core.models.db import Authentication, User
from ehp.core.models.schema import RegistrationSchema
from ehp.core.repositories.authentication import AuthenticationRepository
from ehp.core.repositories.base import BaseRepository
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils import constants as const
from ehp.utils import hash_password, make_response
from ehp.utils.base import (
    log_error,
    log_info,
)

router = APIRouter(responses={404: {"description": "Not found"}})


@router.post("/register", response_class=JSONResponse)
async def register(
    request: Request,
    registration_param: RegistrationSchema,
    session: ManagedAsyncSession,
) -> JSONResponse:

    response_json: Dict[str, Any] = const.ERROR_JSON

    try:
        log_info(f"Registering user: {registration_param.user_email}")
        auth_repo = AuthenticationRepository(session, Authentication)

        # Check if email already exists
        existing_auth = await auth_repo.get_by_email(registration_param.user_email)
        if existing_auth:
            log_info(f"Email already exists: {registration_param.user_email}")
            return JSONResponse(
                content={"error": "An account with this email already exists"},
                status_code=422,
            )

        log_info(f"Creating new user with email: {registration_param.user_email}")

        # Get default profile (assuming there's a default one, or you can hardcode an ID)
        # You might want to adjust this based on your business logic
        # default_profile = await session.get(Profile, 1)  # Assuming profile ID 1 exists

        # Create new authentication record
        new_auth = Authentication(
            user_name=registration_param.user_email,  # Using email as username
            user_email=registration_param.user_email,
            user_pwd=hash_password(registration_param.user_password),
            is_active=const.AUTH_ACTIVE,
            is_confirmed=const.AUTH_CONFIRMED,  # Needs email confirmation
            accept_terms=const.AUTH_ACCEPT_TERMS,
            profile_id=const.PROFILE_IDS.get("user"),  # Default profile ID for users
        )

        created_auth = await auth_repo.create(new_auth)
        log_info(f"Created authentication record for user: {created_auth.user_email}")
        # Create associated user record
        new_user = User(full_name=registration_param.user_name, auth_id=created_auth.id)
        user_repository = BaseRepository(session, User)
        await user_repository.create(new_user)

        # Prepare response data
        log_info(f"User created successfully: {new_user.full_name} ({new_user.id})")
        auth_data = await created_auth.to_dict()
        user_data = await new_user.to_dict()

        # Remove sensitive data from response
        auth_data.pop("user_pwd", None)

        response_json = {
            "code": 200,
            "message": "User registered successfully",
            "auth": auth_data,
            "user": user_data,
        }

    except ValidationError as ve:
        # Handle Pydantic validation errors (password criteria, email format, etc.)
        error_details = ve.errors()[0] if ve.errors() else {}
        error_msg = error_details.get("msg", "Validation error")
        field_name = (
            error_details.get("loc", [""])[0] if error_details.get("loc") else ""
        )
        error_msg = error_details.get("msg", "Validation error")
        field_name = (
            error_details.get("loc", [""])[0] if error_details.get("loc") else ""
        )

        # Return user-friendly error messages
        if "password" in field_name.lower():
            if "characters" in error_msg:
                user_msg = "Password must be at least 8 characters long"
            elif "uppercase" in error_msg:
                user_msg = "Password must contain at least one uppercase letter"
            elif "lowercase" in error_msg:
                user_msg = "Password must contain at least one lowercase letter"
            else:
                user_msg = "Password must be at least 8 characters with uppercase and lowercase letters"
        elif "email" in field_name.lower():
            user_msg = "Please enter a valid email address"
        elif "name" in field_name.lower():
            user_msg = "Name is required"
        else:
            user_msg = "Please check your input and try again"

        return JSONResponse(content={"error": user_msg}, status_code=422)
    except Exception as e:
        log_error(e)

    return make_response(response_json)


@router.post("/registration/{profile_code}", response_class=JSONResponse)
async def registration(
    request: Request,
    profile_code: str,
    registration_param: RegistrationSchema,
) -> JSONResponse:
    try:
        db_manager = request.state.request_config["db_manager"]
        async with db_manager.transaction() as db_session:
            return make_response({})

    except Exception as e:
        await db_session.rollback()
        log_error(e)
    return make_response(const.ERROR_JSON)


# @router.get("/verify/username/<user_name>", response_class=JSONResponse)
# async def verify_username(original_user_name: str) -> JSONResponse:
#     try:
#         auth = await Authentication.get_by_user_name(original_user_name)
#         if not auth:
#             make_response({"user_name_fist": original_user_name})
#
#         user_names: List[Any] = []
#         while len(user_names) < 3:
#             user_name = prefix_random_string(original_user_name, 3)
#             auth = await Authentication.get_by_user_name(user_name)
#             if not auth:
#                 user_names.append(user_name)
#
#         response_json = {
#             "user_name_first": user_names[0],
#             "user_name_second": user_names[1],
#             "user_name_third": user_names[2],
#         }
#
#     except Exception as e:
#         log_error(e)
#         return make_response(const.ERROR_JSON)
#     return make_response(response_json)
#
#
# @router.get("/verify/email/<email>", response_class=JSONResponse)
# async def verify_email(email: str) -> JSONResponse:
#     try:
#         auth = await Authentication.get_by_email(email)
#         return make_response(
#             {
#                 "email_exists": auth is not None,
#                 "user_id": auth.id if auth else None,
#             }
#         )
#     except Exception as e:
#         log_error(e)
#     return make_response(const.ERROR_JSON)
#
#
# @router.get("/check/username/<user_name>", response_class=JSONResponse)
# async def check_username(user_name: str) -> JSONResponse:
#     try:
#         auth = Authentication.get_by_user_name(user_name)
#         return make_response(
#             {
#                 "user_name_exists": auth is not None,
#             }
#         )
#     except Exception as e:
#         log_error(e)
#     return make_response(const.ERROR_JSON)
