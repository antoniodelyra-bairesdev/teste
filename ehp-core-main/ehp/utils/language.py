# from ehp.base.middleware import get_current_request


# def get_language_id() -> int:
#     try:
#         user_session = get_current_request().state.request_config["user_session"]
#         return (
#             user_session.get("session_info", {})
#             .get("person", {})
#             .get("language_id", settings.DEFAULT_LANGUAGE_ID)
#         )
#     except Exception:
#         return (
#             get_current_request().state.request_config["language_id"]
#             or settings.DEFAULT_LANGUAGE_ID
#         )
