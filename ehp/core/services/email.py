from dataclasses import dataclass
from typing import List

from ehp.core.models.db import User
from ehp.utils.email import send_notification


@dataclass
class UserMailer:
    user: User

    def send_mail(
        self,
        subject: str,
        body: str,
        extra_emails: List[str] | None = None,
        force: bool = False,
        include_self: bool = True,
    ) -> bool:
        """
        Sends an email to the user and optionally to extra emails.

        Args:
            subject: The subject of the email.
            body: The body of the email.
            extra_emails: Optional list of additional email addresses.
            force: If True, sends email regardless of user's notification settings.
            include_self: If True, includes user's email in recipients.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        if (
            not force
            and hasattr(self.user, "email_notifications")
            and not self.user.email_notifications
        ):
            return False

        recipients = []
        if (
            include_self
            and hasattr(self.user, "authentication")
            and self.user.authentication.user_email
        ):
            recipients.append(self.user.authentication.user_email)

        if extra_emails:
            recipients.extend(extra_emails)

        if not recipients:
            return False

        return send_notification(subject, body, recipients)
