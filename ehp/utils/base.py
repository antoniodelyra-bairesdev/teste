import asyncio
import base64
import json
import logging
import os
import random
import string
import sys
import traceback
from datetime import datetime
from typing import Any, List

_logger = logging.getLogger(__name__)
_is_in_test = "PYTEST_VERSION" in os.environ

def log_error(error: Any) -> None:
    _logger.error(f"{datetime.now()} ::: {str(error)}")
    if sys.exc_info()[0] and not _is_in_test:
        traceback.print_exc()


def log_debug(msg: Any) -> None:
    _logger.debug(f"{datetime.now()} ::: {str(msg)}")
    if sys.exc_info()[0]:
        traceback.print_exc()


def log_info(msg: Any) -> None:
    _logger.info(f"{datetime.now()} ::: {str(msg)}")
    if sys.exc_info()[0]:
        traceback.print_exc()


def random_pwd(length: int) -> str:
    characters = string.ascii_lowercase + string.digits + string.punctuation
    return "".join(random.choice(characters) for _ in range(length))


def base64_encrypt(text: Any) -> Any:
    if not text:
        return None
    return base64.b64encode(text.encode("UTF-8"))


def base64_decrypt(text: Any) -> Any:
    if not text:
        return None
    return base64.b64decode(text).decode("UTF-8")


def prefix_random_string(original_string: str, length: int) -> str:
    return original_string + generate_random_code(length)


def generate_random_code(length: int) -> str:
    return "".join(random.choice(string.digits) for _ in range(length))


def loads_message(message: str) -> Any:
    try:
        return json.loads(message)
    except Exception:
        return message


async def run_to_dict_async(list_of_objects: List[Any]) -> List[Any]:
    if not list_of_objects:
        return []
    result_tasks = [obj.to_dict() for obj in list_of_objects]
    return await asyncio.gather(*result_tasks) if result_tasks else []
