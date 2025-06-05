from mypy_boto3_secretsmanager.client import SecretsManagerClient


from dataclasses import dataclass
from functools import cached_property

import boto3

from ehp.config import settings


@dataclass
class AWSClient:
    access_key_id: str = settings.AWS_ACCESS_KEY_ID
    secret_access_key: str = settings.AWS_SECRET_ACCESS_KEY
    region_name: str = settings.AWS_REGION_NAME
    endpoint_url: str = settings.AWS_ENDPOINT_URL

    @cached_property
    def secretsmanager_client(self) -> SecretsManagerClient:
        return boto3.Session().client(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region_name,
            service_name="secretsmanager",
            endpoint_url=self.endpoint_url if self.endpoint_url else None,
        )
