from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ehp.config import settings
from ehp.core.models.param import RegistrationParam
from ehp.utils import constants as const
from ehp.utils import hash_password, make_response
from ehp.utils.base import (
    base64_decrypt,
    log_error,
    prefix_random_string,
    run_to_dict_async,
)
from ehp.utils.email import send_notification
from ehp.utils.search import index_content


router = APIRouter(responses={404: {"description": "Not found"}})


@router.post("/registration/{profile_code}", response_class=JSONResponse)
async def registration(
    request: Request,
    profile_code: str,
    registration_param: RegistrationParam,
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
