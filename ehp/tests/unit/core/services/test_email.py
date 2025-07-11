import pytest
from unittest.mock import Mock, patch

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.services.email import UserMailer


@pytest.mark.unit
class TestUserMailer:
    """Unit tests for UserMailer service."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock User with Authentication."""
        user = Mock(spec=User)
        user.authentication = Mock(spec=Authentication)
        user.authentication.user_email = "test@example.com"
        user.email_notifications = True
        return user

    @pytest.fixture
    def user_mailer(self, mock_user) -> UserMailer:
        """Create UserMailer instance with mock user."""
        return UserMailer(mock_user)

    def test_send_mail_no_email(self):
        """Test that send_mail handles user with no email."""
        user = Mock(spec=User)
        user.authentication = Mock(spec=Authentication)
        user.authentication.user_email = None
        user.email_notifications = True

        mailer = UserMailer(user)
        result = mailer.send_mail("Test Subject", "Test Body")

        assert not result, "Should not send email if user has no email"

    def test_send_mail_with_email(self, user_mailer: UserMailer):
        """Test successful email sending."""
        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = user_mailer.send_mail("Test Subject", "Test Body")

            assert result, (
                "Should send email if user has email and notifications enabled"
            )
            mock_send.assert_called_once_with(
                "Test Subject", "Test Body", ["test@example.com"]
            )

    def test_send_mail_notifications_disabled(self, user_mailer: UserMailer):
        """Test that email is not sent when notifications are disabled."""
        user_mailer.user.email_notifications = False

        result = user_mailer.send_mail("Test Subject", "Test Body")

        assert not result, "Should not send email if user has notifications disabled"

    def test_send_mail_with_extra_emails(self, user_mailer: UserMailer):
        """Test sending email with additional recipients."""
        extra_emails = ["another@example.com", "example@test.com"]

        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = user_mailer.send_mail(
                "Test Subject", "Test Body", extra_emails=extra_emails
            )

            assert result, "Should send email with extra emails"
            expected_recipients = ["test@example.com"] + extra_emails
            mock_send.assert_called_once_with(
                "Test Subject", "Test Body", expected_recipients
            )

    def test_send_mail_force_send(self, user_mailer: UserMailer):
        """Test that force=True overrides notification settings."""
        user_mailer.user.email_notifications = False

        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = user_mailer.send_mail("Test Subject", "Test Body", force=True)

            assert result, "Should send email if force is True"
            mock_send.assert_called_once_with(
                "Test Subject", "Test Body", ["test@example.com"]
            )

    def test_send_mail_exclude_self(self, user_mailer: UserMailer):
        """Test sending email without including user's own email."""
        extra_emails = ["another@example.com", "example@test.com"]

        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = user_mailer.send_mail(
                "Test Subject",
                "Test Body",
                extra_emails=extra_emails,
                include_self=False,
            )

            assert result, "Should send email excluding self"
            mock_send.assert_called_once_with(
                "Test Subject", "Test Body", extra_emails
            )

    def test_send_mail_no_recipients(self, user_mailer: UserMailer):
        """Test that email is not sent when there are no recipients."""
        user_mailer.user.authentication.user_email = None

        result = user_mailer.send_mail(
            "Test Subject", "Test Body", include_self=False
        )

        assert not result, "Should not send email if there are no recipients"

    def test_send_mail_no_email_notifications_attribute(self):
        """Test handling user without email_notifications attribute."""
        user = Mock(spec=User)
        user.authentication = Mock(spec=Authentication)
        user.authentication.user_email = "test@example.com"
        # No email_notifications attribute
        del user.email_notifications

        mailer = UserMailer(user)

        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = mailer.send_mail("Test Subject", "Test Body")

            assert result, (
                "Should send email if email_notifications attribute doesn't exist"
            )
            mock_send.assert_called_once_with(
                "Test Subject", "Test Body", ["test@example.com"]
            )
