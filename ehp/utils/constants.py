from typing import Any, Dict, List

ERROR_INVALID_KEY: Dict[str, Any] = {"code": "ERR_01", "message": "ERROR: invalid key"}
ERROR_UNAUTHORIZED: Dict[str, Any] = {
    "code": "ERR_02",
    "message": "ERROR: Unauthorized",
}

PROFILE_ID: Dict[str, Any] = {
    "admin": 1,
    "school": 2,
    "teacher": 3,
    "guardian": 4,
    "student": 5,
}

EMAIL_MSG: str = """ Message received from: <b>{name}</b><br><br>
    <b>Subject: </b>{subject}<br><br>
    <b>Menssage: </b>{message}<br><br>"""

# ERROR CODES
DEACTIVATED_JSON: Dict[str, Any] = {"CODE": 100, "INFO": "DEACTIVATED"}
SUCCESS_JSON: Dict[str, Any] = {"CODE": 200, "INFO": "SUCCESS"}
EMPTY_LIST: Dict[str, Any] = {"CODE": 300, "INFO": "EMPTY LIST"}
EMPTY_VALUE: Dict[str, Any] = {"CODE": 301, "INFO": "EMPTY VALUE"}
ERROR_INVALID_TOKEN: Dict[str, Any] = {"CODE": 302, "INFO": "INVALID X-TOKEN-AUTH"}
ERROR_INVALID_PAYLOAD: Dict[str, Any] = {"CODE": 303, "INFO": "INVALID PAYLOAD"}
ERROR_INVALID_SESSION: Dict[str, Any] = {"CODE": 304, "INFO": "INVALID SESSION"}
ERROR_OPEN_SESSION: Dict[str, Any] = {"CODE": 305, "INFO": "SESSION OPEN"}
ERROR_INVALID_ACCESS: Dict[str, Any] = {"CODE": 306, "INFO": "INVALID ACCESS KEY"}
ERROR_NO_DATA_JSON: Dict[str, Any] = {"CODE": 307, "INFO": "NO DATA FOUND"}
ERROR_INVALID_ACCOUNT_TYPE: Dict[str, Any] = {
    "CODE": 308,
    "INFO": "INVALID ACCOUNT TYPE",
}
ERROR_INVALID_SINN_ID: Dict[str, Any] = {
    "CODE": 400,
    "INFO": "INVALID SINN_ID - YOU SHOULD CREATE A DIGITAL WALLET FIRST.",
}
ERROR_JSON: Dict[str, Any] = {"CODE": 500, "INFO": "GENERAL ERROR"}
ERROR_AUTH: Dict[str, Any] = {"CODE": 501, "INFO": "INVALID LOGIN"}
ERROR_PASSWORD: Dict[str, Any] = {"CODE": 502, "INFO": "INVALID PASSWORD"}
ERROR_USER_EXISTS: Dict[str, Any] = {"CODE": 503, "INFO": "USER EXISTS"}
ERROR_USER_DOES_NOT_EXIST: Dict[str, Any] = {"CODE": 504, "INFO": "USER DOES NOT EXIST"}
ERROR_SCHOOL_DOES_NOT_EXIST: Dict[str, Any] = {
    "CODE": 505,
    "INFO": "SCHOOL DOES NOT EXIST",
}
ERROR_INVENTORY_DOES_NOT_EXIST: Dict[str, Any] = {
    "CODE": 506,
    "INFO": "INVENTORY DOES NOT EXIST",
}
ERROR_INVALID_USER_ID: Dict[str, Any] = {"CODE": 507, "INFO": "INVALID USER ID."}
ERROR_INVALID_SCHOOL_ID: Dict[str, Any] = {
    "CODE": 508,
    "INFO": "INVALID SCHOOL ID.",
}
ERROR_PERSON_DOES_NOT_EXIST: Dict[str, Any] = {
    "CODE": 509,
    "INFO": "PERSON NOT EXIST.",
}
ERROR_INVALID_COMMENT_ID: Dict[str, Any] = {"CODE": 510, "INFO": "INVALID COMMENT ID."}
ERROR_INVALID_PERSON_ID: Dict[str, Any] = {"CODE": 511, "INFO": "INVALID PERSON ID."}
ERROR_INVALID_MANDATORY_ID: Dict[str, Any] = {
    "CODE": 512,
    "INFO": "INVALID MANDATORY ID.",
}
ERROR_USER_DEACTIVATED: Dict[str, Any] = {"CODE": 513, "INFO": "USER DEACTIVATED."}
ERROR_EMAIL_EXISTS: Dict[str, Any] = {"CODE": 514, "INFO": "E-MAIL EXISTS"}
ERROR_SCHOOL_DEACTIVATED: Dict[str, Any] = {"CODE": 516, "INFO": "SCHOOL DEACTIVATED"}
ERROR_INVALID_PROFILE: Dict[str, Any] = {"CODE": 517, "INFO": "INVALID_PROFILE"}
ERROR_CANNOT_REGISTER_STUDENT: Dict[str, Any] = {
    "CODE": 518,
    "INFO": "STUDENTS CANNOT BE REGISTERED HERE.",
}
ERROR_SCHOOL_EXISTS: Dict[str, Any] = {
    "CODE": 519,
    "INFO": "A SCHOOL WITH THIS NAME ALREADY EXIST.",
}
ERROR_INVALID_STUDENT_ID: Dict[str, Any] = {
    "CODE": 520,
    "INFO": "INVALID STUDENT ID.",
}
ERROR_STUDENT_DOES_NOT_EXIST: Dict[str, Any] = {
    "CODE": 521,
    "INFO": "STUDENT DOES NOT EXIST.",
}
ERROR_INVALID_EMAIL: Dict[str, Any] = {"CODE": 522, "INFO": "INVALID EMAIL."}

# Duplicate check constants
DUPLICATE_FOUND: Dict[str, Any] = {"CODE": 523, "INFO": "DUPLICATE ARTICLE FOUND"}
ERROR_INVALID_DUPLICATE_PARAMS: Dict[str, Any] = {"CODE": 525, "INFO": "INVALID DUPLICATE CHECK PARAMETERS"}

ALLOWED_PHOTOS: List[str] = ["png", "jpg", "jpeg", "gif"]
ALLOWED_DOCS_EXTENSIONS: List[str] = ["pdf", "doc", "docx", "txt"]

NOTI_NEW_USER: str = "N_USR"
NOTI_PASSWORD: str = "N_PWD"
NOTI_RESET_PASSWORD: str = "R_PWD"
NOTI_ROUTE_ACTIVATION: str = "activate"
NOTI_ROUTE_RESET_PASSWORD: str = "reset_password"
NOTI_ROUTE_UPDATE_PASSWORD: str = "update_password"
NOTI_ROUTE_PASSWORD: str = "password"
NOTI_ROUTE_INTERNAL: str = "notifica_internal"
NOTI_ROUTE_NOTIFICATION: str = "notification"

DATE_FORMAT: Dict[str, Any] = {
    "full": "%Y-%m-%d %H:%M:%S",
    "date_only": "%Y-%m-%d",
    "time_only": "%H:%M:%S",
    "full_br": "%d/%m/%Y %H:%M:%S",
    "date_only_br": "%d/%m/%Y",
}

AUTH_EVENTS: Dict[str, Any] = {"login": 1, "logout": 2}

AUTH_ACTIVE: str = "1"
AUTH_INACTIVE: str = "0"
AUTH_CONFIRMED: str = "1"
AUTH_NOT_CONFIRMED: str = "0"
AUTH_RESET_PASSWORD: str = "1"
AUTH_ACCEPT_TERMS: str = "1"
AUTH_NOT_ACCEPT_TERMS: str = "0"

PROFILE_IDS: Dict[str, int] = {
    "admin": 1,
    "user": 2,
}

# HTTP Status Code Constants
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_INTERNAL_SERVER_ERROR = 500
