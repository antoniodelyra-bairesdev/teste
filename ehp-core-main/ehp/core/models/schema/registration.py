from ehp.utils.validation import ValidatedModel


class RegistrationSchema(ValidatedModel):
    """Simple enhanced registration model"""
    user_name: str
    user_email: str
    user_password: str
