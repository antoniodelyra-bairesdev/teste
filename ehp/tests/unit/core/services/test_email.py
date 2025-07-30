import pytest
from unittest.mock import AsyncMock, Mock, patch

from ehp.core.models.db.authentication import Authentication
from ehp.core.models.db.user import User
from ehp.core.services.email import UserMailer
from ehp.utils.email import (
    _apply_reading_settings_to_html,
    send_mail,
    send_notification,
)


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

    async def test_send_mail_no_email(self):
        """Test that send_mail handles user with no email."""
        user = Mock(spec=User)
        user.authentication = Mock(spec=Authentication)
        user.authentication.user_email = None
        user.email_notifications = True

        mailer = UserMailer(user)
        result = await mailer.send_mail("Test Subject", "Test Body")

        assert not result, "Should not send email if user has no email"

    async def test_send_mail_with_email(self, user_mailer: UserMailer):
        """Test successful email sending."""
        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = await user_mailer.send_mail("Test Subject", "Test Body")

            assert (
                result
            ), "Should send email if user has email and notifications enabled"
            mock_send.assert_called_once_with(
                "Test Subject",
                "Test Body",
                ["test@example.com"],
                reading_settings=None,
                use_html=False,
            )

    async def test_send_mail_notifications_disabled(self, user_mailer: UserMailer):
        """Test that email is not sent when notifications are disabled."""
        user_mailer.user.email_notifications = False

        result = await user_mailer.send_mail("Test Subject", "Test Body")

        assert not result, "Should not send email if user has notifications disabled"

    async def test_send_mail_with_extra_emails(self, user_mailer: UserMailer):
        """Test sending email with additional recipients."""
        extra_emails = ["another@example.com", "example@test.com"]

        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = await user_mailer.send_mail(
                "Test Subject", "Test Body", extra_emails=extra_emails
            )

            assert result, "Should send email with extra emails"
            expected_recipients = ["test@example.com"] + extra_emails
            mock_send.assert_called_once_with(
                "Test Subject",
                "Test Body",
                expected_recipients,
                reading_settings=None,
                use_html=False,
            )

    async def test_send_mail_force_send(self, user_mailer: UserMailer):
        """Test that force=True overrides notification settings."""
        user_mailer.user.email_notifications = False

        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = await user_mailer.send_mail(
                "Test Subject", "Test Body", force=True
            )

            assert result, "Should send email if force is True"
            mock_send.assert_called_once_with(
                "Test Subject",
                "Test Body",
                ["test@example.com"],
                reading_settings=None,
                use_html=False,
            )

    async def test_send_mail_exclude_self(self, user_mailer: UserMailer):
        """Test sending email without including user's own email."""
        extra_emails = ["another@example.com", "example@test.com"]

        with patch(
            "ehp.core.services.email.send_notification", return_value=True
        ) as mock_send:
            result = await user_mailer.send_mail(
                "Test Subject",
                "Test Body",
                extra_emails=extra_emails,
                include_self=False,
            )

            assert result, "Should send email excluding self"
            mock_send.assert_called_once_with(
                "Test Subject",
                "Test Body",
                extra_emails,
                reading_settings=None,
                use_html=False,
            )

    async def test_send_mail_no_recipients(self, user_mailer: UserMailer):
        """Test that email is not sent when there are no recipients."""
        user_mailer.user.authentication.user_email = None

        result = await user_mailer.send_mail(
            "Test Subject", "Test Body", include_self=False
        )

        assert not result, "Should not send email if there are no recipients"

    async def test_send_mail_no_email_notifications_attribute(self):
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
            result = await mailer.send_mail("Test Subject", "Test Body")

            assert (
                result
            ), "Should send email if email_notifications attribute doesn't exist"
            mock_send.assert_called_once_with(
                "Test Subject",
                "Test Body",
                ["test@example.com"],
                reading_settings=None,
                use_html=False,
            )


@pytest.mark.unit
class TestEmailWithReadingSettings:
    """Unit tests for email functionality with reading settings."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock User with Authentication."""
        user = Mock(spec=User)
        user.id = 123
        user.authentication = Mock(spec=Authentication)
        user.authentication.user_email = "test@example.com"
        user.email_notifications = True
        return user

    @pytest.fixture
    def user_mailer(self, mock_user) -> UserMailer:
        """Create UserMailer instance with mock user."""
        return UserMailer(mock_user)

    @pytest.fixture
    def sample_reading_settings(self):
        """Sample reading settings for testing."""
        return {
            "font_size": "Large",
            "color_mode": "Dark",
            "font_weight": "Bold",
            "line_spacing": "Spacious",
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"},
        }

    def test_apply_reading_settings_to_html_dark_mode(self, sample_reading_settings):
        """Test HTML styling with dark mode settings."""
        html_content = "<p>Test email content</p>"

        result = _apply_reading_settings_to_html(html_content, sample_reading_settings)

        assert "font-size: 18px" in result
        assert "background-color: #1a1a1a" in result
        assert "color: #ffffff" in result
        assert "font-weight: 700" in result
        assert "line-height: 1.8" in result
        assert "font-family: Georgia, serif" in result

    def test_apply_reading_settings_to_html_light_mode(self):
        """Test HTML styling with light mode settings."""
        settings = {
            "font_size": "Small",
            "color_mode": "Light",
            "font_weight": "Light",
            "line_spacing": "Compact",
            "fonts": {"body": "Arial"},
        }
        html_content = "<p>Test email content</p>"

        result = _apply_reading_settings_to_html(html_content, settings)

        assert "font-size: 14px" in result
        assert "background-color: #ffffff" in result
        assert "color: #000000" in result
        assert "font-weight: 300" in result
        assert "line-height: 1.2" in result
        assert "font-family: Arial, sans-serif" in result

    def test_apply_reading_settings_to_html_red_green_color_blindness(self):
        """Test HTML styling with red-green color blindness mode settings."""
        settings = {
            "color_mode": "Red-Green Color Blindness",
            "font_size": "Medium",
        }
        html_content = "<p>Test email content</p>"

        result = _apply_reading_settings_to_html(html_content, settings)

        assert "background-color: #ffffff" in result
        assert "color: #000000" in result
        assert "--accent-color: #0066cc" in result
        assert "font-size: 16px" in result

    def test_apply_reading_settings_with_existing_body_tag(self):
        """Test applying settings to HTML with existing body tag."""
        settings = {
            "font_size": "Large",
            "color_mode": "Dark",
        }
        html_content = "<html><body>Test content</body></html>"

        result = _apply_reading_settings_to_html(html_content, settings)

        # Should modify the existing body tag - check for the style attributes
        assert "font-size: 18px" in result
        assert "background-color: #1a1a1a" in result
        assert "color: #ffffff" in result
        assert "<body" in result

    def test_apply_reading_settings_empty_settings(self):
        """Test HTML styling with empty settings."""
        html_content = "<p>Test email content</p>"

        result = _apply_reading_settings_to_html(html_content, {})

        # Should return original content unchanged
        assert result == html_content

    def test_apply_reading_settings_none_settings(self):
        """Test HTML styling with None settings."""
        html_content = "<p>Test email content</p>"

        result = _apply_reading_settings_to_html(html_content, None)

        # Should return original content unchanged
        assert result == html_content

    def test_font_family_mapping(self):
        """Test various font family mappings."""
        test_cases = [
            ("Arial", "Arial, sans-serif"),
            ("Helvetica", "Helvetica, Arial, sans-serif"),
            ("Georgia", "Georgia, serif"),
            ("Times", "Times, 'Times New Roman', serif"),
            ("Verdana", "Verdana, sans-serif"),
            ("Courier", "'Courier New', monospace"),
            (
                "System",
                "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            ),
            ("Unknown", None),  # Should not add font-family
        ]

        for font_name, expected_css in test_cases:
            settings = {"fonts": {"body": font_name}}
            html_content = "<p>Test</p>"

            result = _apply_reading_settings_to_html(html_content, settings)

            if expected_css:
                assert f"font-family: {expected_css}" in result
            else:
                assert "font-family:" not in result

    def test_font_size_mapping(self):
        """Test font size mapping with all available sizes."""
        test_cases = [
            ("Small", "14px"),
            ("Medium", "16px"),
            ("Large", "18px"),
            ("Unknown", None),  # Should not add font-size
        ]

        for size_name, expected_css in test_cases:
            settings = {"font_size": size_name}
            html_content = "<p>Test</p>"

            result = _apply_reading_settings_to_html(html_content, settings)

            if expected_css:
                assert f"font-size: {expected_css}" in result
            else:
                assert "font-size:" not in result

    def test_line_spacing_mapping(self):
        """Test line spacing mapping with all available options."""
        test_cases = [
            ("Compact", "1.2"),
            ("Standard", "1.5"),
            ("Spacious", "1.8"),
            ("Unknown", None),  # Should not add line-height
        ]

        for spacing_name, expected_css in test_cases:
            settings = {"line_spacing": spacing_name}
            html_content = "<p>Test</p>"

            result = _apply_reading_settings_to_html(html_content, settings)

            if expected_css:
                assert f"line-height: {expected_css}" in result
            else:
                assert "line-height:" not in result

    def test_font_weight_mapping(self):
        """Test font weight mapping with all available options."""
        test_cases = [
            ("Light", "300"),
            ("Normal", "400"),
            ("Bold", "700"),
            ("Unknown", None),  # Should not add font-weight
        ]

        for weight_name, expected_css in test_cases:
            settings = {"font_weight": weight_name}
            html_content = "<p>Test</p>"

            result = _apply_reading_settings_to_html(html_content, settings)

            if expected_css:
                assert f"font-weight: {expected_css}" in result
            else:
                assert "font-weight:" not in result

    def test_wrap_content_in_div_when_no_body_tag(self):
        """Test that content is wrapped in div when no body tag exists."""
        settings = {"font_size": "Large", "color_mode": "Dark"}
        html_content = "<p>Test content</p>"

        result = _apply_reading_settings_to_html(html_content, settings)

        assert result.startswith('<div style="')
        assert result.endswith("</div>")
        assert "font-size: 18px" in result
        assert "background-color: #1a1a1a" in result

    def test_blue_yellow_color_blindness_mode(self):
        """Test HTML styling with blue-yellow color blindness mode settings."""
        settings = {
            "color_mode": "Blue-Yellow Color Blindness",
            "font_size": "Medium",
        }
        html_content = "<p>Test email content</p>"

        result = _apply_reading_settings_to_html(html_content, settings)

        assert "background-color: #ffffff" in result
        assert "color: #000000" in result
        assert "--accent-color: #cc0000" in result
        assert "font-size: 16px" in result

    def test_headline_font_application(self):
        """Test that headline fonts are applied to heading tags."""
        settings = {
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"}
        }
        html_content = "<h1>Title</h1><p>Body text</p><h2>Subtitle</h2>"

        result = _apply_reading_settings_to_html(html_content, settings)

        # Check that headline font is applied to h1 and h2 tags
        assert 'style="font-family: Arial, sans-serif;"' in result
        # Check that body font is applied as base style
        assert "font-family: Georgia, serif" in result

    def test_caption_font_application(self):
        """Test that caption fonts are applied to caption tags."""
        settings = {
            "fonts": {"headline": "Arial", "body": "Georgia", "caption": "Verdana"}
        }
        html_content = (
            "<p>Body text</p><small>Caption text</small>"
            "<figcaption>Figure caption</figcaption>"
        )

        result = _apply_reading_settings_to_html(html_content, settings)

        # Check that caption font is applied to small and figcaption tags
        assert 'style="font-family: Verdana, sans-serif;"' in result
        # Check that body font is applied as base style
        assert "font-family: Georgia, serif" in result

    def test_system_font_not_applied_to_elements(self):
        """Test that System font is not applied to specific elements."""
        settings = {
            "fonts": {"headline": "System", "body": "Georgia", "caption": "System"}
        }
        html_content = "<h1>Title</h1><p>Body text</p><small>Caption</small>"

        result = _apply_reading_settings_to_html(html_content, settings)

        # System fonts should not be applied to headline and caption elements
        assert 'style="font-family:' not in result
        # Only body font should be applied
        assert "font-family: Georgia, serif" in result

    @patch("ehp.utils.email.smtplib.SMTP")
    def test_send_mail_with_reading_settings_html(
        self, mock_smtp, sample_reading_settings
    ):
        """Test sending HTML email with reading settings."""
        html_body = "<h1>Welcome!</h1><p>This is a test email.</p>"
        recipients = ["test@example.com"]

        # Mock SMTP
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_mail(
            "Test Subject",
            html_body,
            recipients,
            reading_settings=sample_reading_settings,
            use_html=True,
        )

        assert result is True
        mock_server.send_message.assert_called_once()

        # Verify the message was constructed properly
        call_args = mock_server.send_message.call_args[0][0]
        assert call_args.is_multipart()  # Should be multipart for HTML email

    @patch("ehp.utils.email.smtplib.SMTP")
    def test_send_mail_plain_text_no_settings(self, mock_smtp):
        """Test sending plain text email without reading settings."""
        body = "This is a plain text email."
        recipients = ["test@example.com"]

        # Mock SMTP
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_mail("Test Subject", body, recipients)

        assert result is True
        mock_server.send_message.assert_called_once()

        # Verify the message was constructed as plain text
        call_args = mock_server.send_message.call_args[0][0]
        assert not call_args.is_multipart()  # Should be single part for plain text

    @patch("ehp.utils.email.smtplib.SMTP")
    def test_send_mail_html_without_reading_settings(self, mock_smtp):
        """Test sending HTML email without reading settings."""
        html_body = "<h1>Test</h1><p>HTML content</p>"
        recipients = ["test@example.com"]

        # Mock SMTP
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = send_mail("Test Subject", html_body, recipients, use_html=True)

        assert result is True
        mock_server.send_message.assert_called_once()

        # Should be plain text when use_html=True but reading_settings=None
        call_args = mock_server.send_message.call_args[0][0]
        assert not call_args.is_multipart()

    def test_send_mail_validation_empty_parameters(self):
        """Test send_mail validation with empty parameters."""
        # Test empty subject
        result = send_mail("", "Test body", ["test@example.com"])
        assert result is False

        # Test empty body
        result = send_mail("Test subject", "", ["test@example.com"])
        assert result is False

        # Test empty recipients
        result = send_mail("Test subject", "Test body", [])
        assert result is False

        # Test None parameters
        result = send_mail(None, "Test body", ["test@example.com"])
        assert result is False

        result = send_mail("Test subject", None, ["test@example.com"])
        assert result is False

    @patch("ehp.utils.email.send_mail")
    def test_send_notification_with_settings(
        self, mock_send_mail, sample_reading_settings
    ):
        """Test send_notification function with reading settings."""
        mock_send_mail.return_value = True

        result = send_notification(
            "Test Subject",
            "<p>Test HTML content</p>",
            ["test@example.com"],
            reading_settings=sample_reading_settings,
            use_html=True,
        )

        assert result is True
        mock_send_mail.assert_called_once_with(
            "Test Subject",
            "<p>Test HTML content</p>",
            ["test@example.com"],
            sample_reading_settings,
            True,
        )

    @patch("ehp.utils.email.send_mail")
    def test_send_notification_plain_text(self, mock_send_mail):
        """Test send_notification function with plain text."""
        mock_send_mail.return_value = True

        result = send_notification(
            "Test Subject",
            "Plain text content",
            ["test@example.com"],
        )

        assert result is True
        mock_send_mail.assert_called_once_with(
            "Test Subject",
            "Plain text content",
            ["test@example.com"],
            None,
            False,
        )

    async def test_user_mailer_with_reading_settings(
        self, user_mailer, sample_reading_settings
    ):
        """Test UserMailer with reading settings integration."""
        mock_session = AsyncMock()

        with patch("ehp.core.services.email.UserRepository") as mock_user_repo:
            with patch("ehp.core.services.email.send_notification") as mock_send:
                # Mock repository
                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_reading_settings.return_value = (
                    sample_reading_settings
                )
                mock_user_repo.return_value = mock_repo_instance

                # Mock send_notification
                mock_send.return_value = True

                # Call send_mail with HTML enabled
                result = await user_mailer.send_mail(
                    "Test Subject",
                    "<h1>Test HTML Email</h1>",
                    db_session=mock_session,
                    use_html=True,
                )

                assert result is True
                mock_send.assert_called_once()

                # Verify reading_settings parameter was passed
                call_args = mock_send.call_args
                assert call_args[1]["reading_settings"] == sample_reading_settings
                assert call_args[1]["use_html"] is True

    async def test_user_mailer_db_session_error(self, user_mailer):
        """Test UserMailer handles database session errors gracefully."""
        mock_session = AsyncMock()

        with patch("ehp.core.services.email.UserRepository") as mock_user_repo:
            with patch("ehp.core.services.email.send_notification") as mock_send:
                # Mock repository to raise exception
                mock_user_repo.side_effect = Exception("Database error")

                # Mock send_notification
                mock_send.return_value = True

                # Call send_mail - should handle error gracefully
                result = await user_mailer.send_mail(
                    "Test Subject",
                    "<h1>Test HTML Email</h1>",
                    db_session=mock_session,
                    use_html=True,
                )

                assert result is True
                mock_send.assert_called_once()

                # Verify reading_settings was None due to error
                call_args = mock_send.call_args
                assert call_args[1]["reading_settings"] is None

    async def test_user_mailer_no_db_session(self, user_mailer):
        """Test UserMailer works without database session."""
        with patch("ehp.core.services.email.send_notification") as mock_send:
            mock_send.return_value = True

            # Call without db_session
            result = await user_mailer.send_mail("Test Subject", "Test email body")

            assert result is True
            mock_send.assert_called_once()

            # Verify no reading_settings parameter
            call_args = mock_send.call_args
            assert call_args[1]["reading_settings"] is None
            assert call_args[1]["use_html"] is False

    async def test_user_mailer_use_html_false_with_db_session(
        self, user_mailer, sample_reading_settings
    ):
        """Test UserMailer ignores reading settings when use_html=False."""
        mock_session = AsyncMock()

        with patch("ehp.core.services.email.UserRepository") as mock_user_repo:
            with patch("ehp.core.services.email.send_notification") as mock_send:
                # Mock repository
                mock_repo_instance = AsyncMock()
                mock_repo_instance.get_reading_settings.return_value = (
                    sample_reading_settings
                )
                mock_user_repo.return_value = mock_repo_instance

                # Mock send_notification
                mock_send.return_value = True

                # Call send_mail with use_html=False
                result = await user_mailer.send_mail(
                    "Test Subject",
                    "Plain text email",
                    db_session=mock_session,
                    use_html=False,
                )

                assert result is True
                mock_send.assert_called_once()

                # Verify reading_settings was not fetched
                mock_repo_instance.get_reading_settings.assert_not_called()
                call_args = mock_send.call_args
                assert call_args[1]["reading_settings"] is None
                assert call_args[1]["use_html"] is False
