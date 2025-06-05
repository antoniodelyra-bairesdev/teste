from moto import mock_aws

from ehp.base.aws import AWSClient


@mock_aws
def test_aws_client_secrets_manager() -> None:
    """
    Test the AWSClient's secrets manager functionality.
    """
    aws_client = AWSClient()
    secret_name = "test_secret"
    aws_client.secretsmanager_client.create_secret(
        Name=secret_name, SecretString="my_secret_value"
    )
    secret_value = aws_client.secretsmanager_client.get_secret_value(
        SecretId=secret_name
    )
    assert secret_value is not None
    assert "SecretString" in secret_value
    assert secret_value["SecretString"] == "my_secret_value"
