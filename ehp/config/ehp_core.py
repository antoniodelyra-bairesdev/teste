import os
from datetime import datetime
from typing import Any, Dict

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = os.environ["APP_NAME"]
    APP_DESCRIPTION: str = os.environ.get("APP_DESCRIPTION", "")
    APP_VERSION: str = os.environ["APP_VERSION"]
    APP_ENCODING_ALG: str = os.environ.get("APP_ENCODING_ALG", "HS256")
    APP_ISSUER: str = os.environ["APP_ISSUER"]
    APP_JWT_ENABLED: bool = os.environ["APP_JWT_ENABLED"] == "True"
    APP_LOG_NAME: str = os.environ["APP_LOG_NAME"]
    DEBUG: bool = os.environ["DEBUG"] == "True"

    APP_URL: str = os.environ.get("APP_URL", "http://localhost:17000")

    DATABASE_URL: str = os.environ["DATABASE_URL"]
    DATABASE_PORT: int = int(os.environ["DATABASE_PORT"])
    POSTGRES_DB: str = os.environ["POSTGRES_DB"]
    POSTGRES_USER: str = os.environ["POSTGRES_USER"]
    POSTGRES_PASSWORD: str = os.environ["POSTGRES_PASSWORD"]
    SQLALCHEMY_DATABASE_URI: str = (
        f"postgresql+psycopg2://{POSTGRES_USER}:"
        f"{POSTGRES_PASSWORD}@{DATABASE_URL}:"
        f"{DATABASE_PORT}/{POSTGRES_DB}"
    )
    SQLALCHEMY_ASYNC_DATABASE_URI: str = (
        f"postgresql+asyncpg://{POSTGRES_USER}:"
        f"{POSTGRES_PASSWORD}@{DATABASE_URL}:"
        f"{DATABASE_PORT}/{POSTGRES_DB}"
    )
    SQLALCHEMY_ECHO: bool = bool(os.environ["SQLALCHEMY_ECHO"] == "True")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = bool(
        os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS", "False") == "True"
    )
    # type: ignore
    POOL_RECYCLE: int = int(os.environ.get("SQLALCHEMY_POOL_RECYCLE", 299))
    # type: ignore
    POOL_TIMEOUT: int = int(os.environ.get("SQLALCHEMY_POOL_TIMEOUT", 20))

    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        "pool_recycle": POOL_RECYCLE,
        "pool_timeout": POOL_TIMEOUT,
    }
    ITEMS_PER_PAGE: int = 20
    MAX_ITEMS_PER_PAGE: int = 200
    DEFAULT_LANGUAGE: str = os.environ.get("DEFAULT_LANGUAGE", "en_US")
    DEPLOYED_AT: str = str(datetime.now())

    REDIS_HOST: str = os.environ["REDIS_HOST"]
    REDIS_PORT: int = int(os.environ["REDIS_PORT"])
    SESSION_TIMEOUT: int = int(os.environ["SESSION_TIMEOUT"])
    SESSION_COOKIE_NAME: str = os.environ["SESSION_COOKIE_NAME"]

    ELASTICSEARCH_URL: str = os.environ["ELASTICSEARCH_URL"]

    API_KEY_NAME: str = "X-Api-Key"
    SECRET_KEY: str = "61a9fd867e810f7e846946bd3ba4e0c6ebae2d39b9bfe7c276a40250a8942d83"
    API_KEY_VALUE: str = os.environ.get(
        "API_KEY_VALUE", "52b23c0a-cf59-48ef-be2f-921c45377ac8"
    )
    AUTH_TOKEN_NAME: str = "x-token-auth"
    ACTIVE_SESSION_PARAM: str = "auth_info"
    PROFILE_INFO: str = "profile_info"

    SYS_AUTH_SENDER_ID: int = 1

    EMAIL_USER: str = os.environ["EMAIL_USER"]
    EMAIL_PASSWORD: str = os.environ["EMAIL_PASSWORD"]
    EMAIL_SENDER: str = os.environ["EMAIL_SENDER"]
    EMAIL_HOST: str = os.environ["EMAIL_HOST"]
    EMAIL_PORT: int = int(os.environ["EMAIL_PORT"])
    EMAIL_NAME: str = os.environ["EMAIL_NAME"]
    CONTACT_EMAIL: str = os.environ["CONTACT_EMAIL"]
    CONTACT_PHONE: str = os.environ["CONTACT_PHONE"]

    ES_KEY: str = os.environ["ES_KEY"]
    JOIN_DEPTH: int = 1

    ETAI_API_KEY: str = os.environ.get("ETAI_API_KEY", "default-secret-etai")

    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION_NAME: str = os.environ.get("AWS_REGION_NAME", "us-east-1")
    AWS_ENDPOINT_URL: str = os.environ.get("AWS_ENDPOINT_URL", "")
    AWS_S3_BUCKET: str = os.environ.get("AWS_S3_BUCKET", "ehp-bucket")

    LOGIN_ERROR_TIMEOUT: int = int(os.environ.get("LOGIN_ERROR_TIMEOUT", 60))
    LOGIN_ERROR_MAX_RETRY: int = int(os.environ.get("LOGIN_ERROR_MAX_RETRY", 5))


settings = Settings()
