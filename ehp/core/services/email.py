from dataclasses import dataclass

from ehp.core.models.db import User
from ehp.core.repositories.user import UserRepository
from ehp.utils.email import send_notification
from ehp.utils.base import log_error


@dataclass
class UserMailer:
    user: User

    async def send_mail(
        self,
        subject: str,
        body: str,
        extra_emails: list[str] | None = None,
        force: bool = False,
        include_self: bool = True,
        db_session=None,
        use_html: bool = False,
    ) -> bool:
        """
        Sends an email to the user and optionally to extra emails.
        Now includes reading settings for HTML email styling.

        Args:
            subject: The subject of the email.
            body: The body of the email.
            extra_emails: Optional list of additional email addresses.
            force: If True, sends email regardless of user's notification settings.
            include_self: If True, includes user's email in recipients.
            db_session: Database session for fetching reading settings.
            use_html: If True, applies reading settings styling to HTML email.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        # Validate required parameters
        if not subject or not body:
            log_error("Email subject and body cannot be empty")
            return False

        # Check user notification preferences
        if (
            not force
            and hasattr(self.user, "email_notifications")
            and not self.user.email_notifications
        ):
            log_error(f"Email notifications disabled for user {self.user.id}")
            return False

        # Build recipients list
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
            log_error("No valid recipients found for email")
            return False

        # Get reading settings if HTML email and db_session provided
        reading_settings = None
        if use_html and db_session:
            try:
                user_repo = UserRepository(db_session)
                reading_settings = await user_repo.get_reading_settings(self.user.id)
            except Exception as e:
                log_error(f"Failed to get reading settings for email: {e}")
                # Continue without reading settings rather than failing

        return send_notification(
            subject, 
            body, 
            recipients, 
            reading_settings=reading_settings,
            use_html=use_html
        )
