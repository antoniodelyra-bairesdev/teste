from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from ehp.base import (
    create_redis_session,
    get_from_redis_session,
    remove_from_redis_session,
)
from ehp.core.models.db import (
    Authentication,
    AuthenticationLog,
    AuthEvent,
)
from ehp.core.models.param import AuthenticationParam
from ehp.utils import check_password, make_response, needs_token_auth
from ehp.utils import constants as const
from ehp.utils.base import base64_decrypt, log_error, run_to_dict_async


auth_router = APIRouter(
    responses={404: {"description": "Not found"}},
)


logout_router = APIRouter(
    dependencies=[Depends(needs_token_auth)],
    responses={404: {"description": "Not found"}},
)


@auth_router.post("/authenticate", response_class=JSONResponse)
async def authenticate(
    request: Request,
    auth_param: AuthenticationParam,
) -> JSONResponse:
    response_json: Dict[str, Any] = const.ERROR_JSON
    try:
        email = auth_param.user_email
        username = auth_param.user_name
        # db_manager = request.state.request_config["db_manager"]
        # async with db_manager.transaction() as db_session:

        auth: Optional[Authentication] = None
        if email:
            auth = await Authentication.get_by_email(email)

        if not auth and username:
            auth = await Authentication.get_by_user_name(username)

        if not auth:
            response_json = const.ERROR_USER_DOES_NOT_EXIST
        else:
            if auth.is_active == const.AUTH_INACTIVE:
                response_json = const.ERROR_USER_DEACTIVATED

            if (
                auth.profile_id == const.PROFILE_ID["school"]
                and auth.person
                and auth.person.school
                and (
                    auth.person.school.is_active == const.AUTH_INACTIVE
                    or not check_last_payment(auth.person.school)
                )
            ):
                return make_response(const.ERROR_SCHOOL_DEACTIVATED)

            if auth.is_confirmed == const.AUTH_CONFIRMED and check_password(
                auth.user_pwd, base64_decrypt(auth_param.user_pwd)
            ):
                language_id = auth.person.language_id
                if hasattr(request.state, "request_config"):
                    request.state.request_config["language_id"] = language_id
                else:
                    request.state.request_config = {"language_id": language_id}

                auth_json = await auth.to_dict()
                session_token = create_redis_session(auth_json)
                """
                {
                    "admin": 1,
                    "school": 2,
                    "teacher": 3,
                    "guardian": 4,
                    "student": 5,
                }
                """

                if auth.profile_id in [
                    const.PROFILE_ID["guardian"],
                    const.PROFILE_ID["teacher"],
                ]:
                    _students = auth.person.students
                    students = await run_to_dict_async(_students)
                else:
                    students = []

                response_json = {
                    "session_token": session_token,
                    **auth_json,
                    "students": students,
                }

                if response_json:
                    await _auth_log(request, auth_json, AuthEvent.LOGGED_IN.value)
            else:
                response_json = const.ERROR_PASSWORD
            # await db_session.flush()

    except Exception as e:
        log_error(e)

    return make_response(response_json)


@logout_router.get("/logout", response_class=JSONResponse)
async def logout(
    request: Request,
    x_token_auth: Annotated[str, Header()],
) -> JSONResponse:
    logout_message: str = "Logged out successfully."
    try:
        session_data = get_from_redis_session(x_token_auth)
        await _auth_log(
            request,
            session_data.get("session_info"),
            AuthEvent.LOGGED_IN.value,
        )
        remove_from_redis_session(x_token_auth)
    except Exception as e:
        log_error(e)
        logout_message = str(e)
    return make_response({"message": logout_message})


async def _auth_log(
    request: Request, auth_info: Dict[str, Any], auth_event: str
) -> None:
    try:
        db_manager = request.state.request_config["db_manager"]
        async with db_manager.transaction() as db_session:
            user_id = auth_info.get("id")
            auth_log = AuthenticationLog()
            auth_log.ip_address = request.client.host
            auth_log.description = f"User: {auth_info.get('user_name')} {auth_event}."
            auth_log.auth_id = user_id
            auth_log.auth_event = auth_event
            db_session.add(auth_log)
            await db_session.flush()
    except Exception as e:
        log_error(e)
