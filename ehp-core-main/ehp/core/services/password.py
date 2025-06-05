# from typing import Any, Dict
#
# from fastapi import APIRouter, Depends, Request
# from fastapi.responses import JSONResponse
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from ehp.core.repositories.authentication import AuthenticationRepository
# from ehp.core.services.dependencies import get_session
# from ehp.config import settings
# from ehp.core.models.db import Authentication
# from ehp.core.models.db.structure import Notification, NotificationTemplate
# from ehp.core.models.schema import AuthenticationSchema, PasswordSchema
# from ehp.utils import (
#     check_password,
#     hash_password,
#     make_response,
#     needs_api_key,
#     needs_token_auth,
# )
# from ehp.utils import constants as const
# from ehp.utils.email import send_notification
# from ehp.utils.base import (
#     base64_decrypt,
#     generate_random_code,
#     log_error,
#     random_pwd,
# )
#
#
# router = APIRouter(
#     dependencies=[
#         Depends(needs_api_key),
#         Depends(needs_token_auth),
#     ],
#     responses={404: {"description": "Not found"}},
# )
#
#
# async def user_password(
#         request: Request,
#         pwd_param: PasswordSchema,
#         session: AsyncSession = Depends(get_session),
# ) -> JSONResponse:
#     response_json: Dict[str, Any] = const.ERROR_JSON
#
#     try:
#         from ehp.core.models.db import Authentication
#
#         auth_repo = AuthenticationRepository(session, Authentication)
#         auth = await auth_repo.get_by_id(pwd_param.auth_id)
#
#         if auth:
#             if auth.user_email != pwd_param.user_email:
#                 return make_response(const.ERROR_INVALID_EMAIL)
#
#             auth.reset_password = "1"
#             auth.reset_code = "1234"  # Generate proper code
#             await auth_repo.update(auth)
#
#             response_json = const.SUCCESS_JSON
#         else:
#             response_json = const.ERROR_USER_DOES_NOT_EXIST
#
#     except Exception as e:
#         log_error(e)
#
#     return make_response(response_json)
#
#
# @router.put("/user/validate/code", response_class=JSONResponse)
# async def validate_code(pwd_param: PasswordSchema) -> JSONResponse:
#     response_json: Dict[str, Any] = const.ERROR_JSON
#     try:
#         auth_id = pwd_param.auth_id
#         reset_code = pwd_param.reset_code
#         auth = await Authentication.get_by_id(auth_id)
#         if not auth:
#             return make_response(const.ERROR_USER_DOES_NOT_EXIST)
#
#         response_json = {"code_is_valid": auth.reset_code == reset_code}
#
#     except Exception as e:
#         log_error(e)
#
#     return make_response(response_json)
#
#
# @router.post("/user/pwd/update", response_class=JSONResponse)
# async def update_password(request: Request, pwd_param: PasswordSchema) -> JSONResponse:
#     response_json: Dict[str, Any] = const.ERROR_JSON
#     try:
#         email = pwd_param.user_email
#         old_password = pwd_param.old_password
#         new_password = pwd_param.user_password
#
#         db_manager = request.state.request_config["db_manager"]
#         async with db_manager.transaction() as db_session:
#             auth = await Authentication.get_by_email(email)
#             if not auth:
#                 response_json = const.ERROR_USER_DOES_NOT_EXIST
#
#             # Check if old password matches the current password
#             if not check_password(auth.user_pwd, base64_decrypt(old_password)):
#                 response_json = const.ERROR_PASSWORD
#
#             # Update password
#             auth.user_pwd = hash_password(base64_decrypt(new_password))
#             await db_session.flush()
#             response_json = const.SUCCESS_JSON
#
#     except Exception as e:
#         log_error(e)
#     return make_response(response_json)
#
#
# @router.post("/user/pwd/recover", response_class=JSONResponse)
# async def recover_password(
#     request: Request,
#     auth_param: AuthenticationSchema,
# ) -> JSONResponse:
#     response_json: Dict[str, Any] = const.ERROR_JSON
#     try:
#         email = auth_param.user_email
#
#         db_manager = request.state.request_config["db_manager"]
#         async with db_manager.transaction() as db_session:
#             auth = await Authentication.get_by_email(email)
#
#             if not auth:
#                 response_json = const.ERROR_USER_DOES_NOT_EXIST
#
#             if auth.active == const.AUTH_INACTIVE:
#                 response_json = const.ERROR_USER_DEACTIVATED
#
#             if auth.confirmed != const.AUTH_CONFIRMED:
#                 response_json = const.ERROR_INVALID_ACCESS
#
#             _random_pwd = random_pwd(8)
#             auth.user_pwd = hash_password(_random_pwd)
#             auth.reset_password = const.AUTH_RESET_PASSWORD
#             try:
#                 template = await NotificationTemplate.get_by_code(const.NOTI_PASSWORD)
#                 if template:
#                     notification = Notification(
#                         template.subject,
#                         template.description,
#                         template.id,
#                         settings.SYS_AUTH_SENDER_ID,
#                     )
#                     notification.auth_receiver = auth
#                     db_session.add(notification)
#
#                     if send_notification(
#                         notification.subject,
#                         notification.description,
#                         auth.user_email,
#                         const.NOTI_ROUTE_PASSWORD,
#                         _random_pwd,
#                     ):
#                         notification.sent = const.AUTH_CONFIRMED
#                     else:
#                         # schedule para re-envio!!!
#                         notification.sent = const.AUTH_NOT_CONFIRMED
#             except Exception as e:
#                 log_error(e)
#
#             await db_session.flush()
#             response_json = const.SUCCESS_JSON
#
#     except Exception as e:
#         log_error(e)
#     return make_response(response_json)
#
#
# @router.put("/user/pwd/reset", response_class=JSONResponse)
# async def reset_password(
#     request: Request,
#     pwd_param: PasswordSchema,
# ) -> JSONResponse:
#     response_json: Dict[str, Any] = const.ERROR_JSON
#     try:
#         auth_id = pwd_param.auth_id
#         user_email = pwd_param.user_email
#         user_pwd = pwd_param.user_password
#
#         db_manager = request.state.request_config["db_manager"]
#         async with db_manager.transaction() as db_session:
#             auth = await Authentication.get_by_id(auth_id)
#             if auth:
#                 if auth.user_email != user_email:
#                     return make_response(const.ERROR_INVALID_EMAIL)
#
#                 if auth.reset_password != "1":
#                     return make_response(const.ERROR_UNAUTHORIZED)
#
#                 auth.reset_password = "0"
#                 auth.reset_code = None
#                 auth.user_pwd = hash_password(base64_decrypt(user_pwd))
#                 await db_session.flush()
#
#                 send_notification(
#                     "Password was Reset",
#                     (
#                         "Your password was just reset. If you did not request this, please"
#                         " contact us."
#                     ),
#                     auth.user_email,
#                     "",
#                     auth.id,
#                 )
#                 response_json = const.SUCCESS_JSON
#             else:
#                 response_json = const.ERROR_USER_DOES_NOT_EXIST
#     except Exception as e:
#         log_error(e)
#
#     return make_response(response_json)
