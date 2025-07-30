import re
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from ehp.config import settings
from ehp.utils.base import log_error


def _apply_reading_settings_to_html(
    html_body: str, reading_settings: dict | None
) -> str:
    """
    Apply user's reading settings as inline CSS styles to HTML email.

    Args:
        html_body: The HTML content of the email
        reading_settings: User's reading settings dictionary

    Returns:
        HTML with inline styles applied
    """
    if not reading_settings:
        return html_body

    # Extract settings with defaults
    font_size = reading_settings.get("font_size", "Medium")
    color_mode = reading_settings.get("color_mode", "Default")
    font_weight = reading_settings.get("font_weight", "Normal")
    line_spacing = reading_settings.get("line_spacing", "Standard")
    fonts = reading_settings.get("fonts", {})

    # Convert settings to CSS values
    css_styles = []

    # Font size mapping (Small, Medium, Large)
    font_size_map = {
        "Small": "14px",
        "Medium": "16px", 
        "Large": "18px",
    }
    if font_size in font_size_map:
        css_styles.append(f"font-size: {font_size_map[font_size]}")

    # Color mode mapping with accessibility options
    if color_mode == "Dark":
        css_styles.append("background-color: #1a1a1a")
        css_styles.append("color: #ffffff")
    elif color_mode == "Light":
        css_styles.append("background-color: #ffffff")
        css_styles.append("color: #000000")
    elif color_mode == "Red-Green Color Blindness":
        # High contrast colors optimized for red-green color blindness
        css_styles.append("background-color: #ffffff")
        css_styles.append("color: #000000")
        # Use blue instead of red/green for emphasis
        css_styles.append("--accent-color: #0066cc")
    elif color_mode == "Blue-Yellow Color Blindness":
        # High contrast colors optimized for blue-yellow color blindness
        css_styles.append("background-color: #ffffff")
        css_styles.append("color: #000000")
        # Use red instead of blue/yellow for emphasis
        css_styles.append("--accent-color: #cc0000")

    # Font weight mapping (Light, Normal, Bold)
    font_weight_map = {"Light": "300", "Normal": "400", "Bold": "700"}
    if font_weight in font_weight_map:
        css_styles.append(f"font-weight: {font_weight_map[font_weight]}")

    # Line spacing mapping (Compact, Standard, Spacious)
    line_spacing_map = {
        "Compact": "1.2",
        "Standard": "1.5",
        "Spacious": "1.8",
    }
    if line_spacing in line_spacing_map:
        css_styles.append(f"line-height: {line_spacing_map[line_spacing]}")

    # Font family mapping for different text elements
    headline_font = fonts.get("headline", "System")
    body_font = fonts.get("body", "System")
    caption_font = fonts.get("caption", "System")

    # Map common font names to CSS font stacks
    font_stack_map = {
        "Arial": "Arial, sans-serif",
        "Helvetica": "Helvetica, Arial, sans-serif",
        "Georgia": "Georgia, serif",
        "Times": "Times, 'Times New Roman', serif",
        "Verdana": "Verdana, sans-serif",
        "Courier": "'Courier New', monospace",
        "System": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }

    # Apply body font as base style
    if body_font in font_stack_map:
        css_styles.append(f"font-family: {font_stack_map[body_font]}")

    # Apply styles by wrapping content in a styled div
    if css_styles:
        style_string = "; ".join(css_styles)
        
        # If the HTML already has a body tag, add styles to it
        if "<body" in html_body.lower():
            # Add style to existing body tag
            pattern = r"<body([^>]*)>"
            replacement = f'<body\\1 style="{style_string}">'
            html_body = re.sub(pattern, replacement, html_body, flags=re.IGNORECASE)
        else:
            # Wrap content in a styled div
            html_body = f'<div style="{style_string}">{html_body}</div>'

        # Apply specific font styles to different elements if they exist
        if headline_font in font_stack_map and headline_font != "System":
            headline_style = f"font-family: {font_stack_map[headline_font]};"
            # Apply to h1, h2, h3, h4, h5, h6 tags
            for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                pattern = rf"<{tag}([^>]*)>"
                replacement = f'<{tag}\\1 style="{headline_style}">'
                html_body = re.sub(pattern, replacement, html_body, flags=re.IGNORECASE)

        if caption_font in font_stack_map and caption_font != "System":
            caption_style = f"font-family: {font_stack_map[caption_font]};"
            # Apply to small, caption, figcaption tags
            for tag in ["small", "caption", "figcaption"]:
                pattern = rf"<{tag}([^>]*)>"
                replacement = f'<{tag}\\1 style="{caption_style}">'
                html_body = re.sub(pattern, replacement, html_body, flags=re.IGNORECASE)

    return html_body


def send_mail(
    subject: str,
    body: str,
    recipients: list[str],
    reading_settings: dict | None = None,
    use_html: bool = False,
) -> bool:
    """
    Sends an email to a list of recipients with optional reading settings styling.

    Args:
        subject: The subject of the email.
        body: The body of the email.
        recipients: A list of recipient email addresses.
        reading_settings: Optional user reading settings for HTML styling.
        use_html: Whether to send as HTML email with styling applied.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not all([subject, body, recipients]):
        log_error("Email subject, body, and recipients cannot be empty.")
        return False

    try:
        # Create the email message object
        if use_html and reading_settings:
            # Create multipart message for HTML
            msg = MIMEMultipart("alternative")

            # Apply reading settings to HTML body
            styled_html = _apply_reading_settings_to_html(body, reading_settings)

            # Create plain text version (strip HTML tags for fallback)
            plain_text = re.sub(r"<[^>]+>", "", body)

            # Create both plain and HTML parts
            text_part = MIMEText(plain_text, "plain", _charset="UTF-8")
            html_part = MIMEText(styled_html, "html", _charset="UTF-8")

            msg.attach(text_part)
            msg.attach(html_part)
        else:
            # Create plain text message
            msg = MIMEText(body, "plain", _charset="UTF-8")

        msg["Subject"] = subject

        # Set the "From" header with a friendly name
        msg["From"] = formataddr(
            (str(Header(settings.EMAIL_NAME, "utf-8")), settings.EMAIL_SENDER)
        )

        # Join the list of recipients into a single comma-separated string for the 'To' header
        msg["To"] = ", ".join(recipients)

        # Use a 'with' statement for automatic resource management (ensures s.quit() is called)
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as s:
            s.set_debuglevel(0)  # Set to 1 to see detailed SMTP logs
            s.starttls()  # Upgrade the connection to a secure one
            s.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)

            # The send_message method is modern and handles headers correctly.
            # The 'recipients' list is used for the SMTP envelope.
            s.send_message(msg, from_addr=settings.EMAIL_SENDER, to_addrs=recipients)

            log_error(f"Email sent successfully to: {', '.join(recipients)}")
            return True

    except smtplib.SMTPAuthenticationError as e:
        log_error(
            f"SMTP authentication error: Failed to log in. Check credentials. ({e})"
        )
    except smtplib.SMTPConnectError as e:
        log_error(f"SMTP connection error: Failed to connect to the server. ({e})")
    except smtplib.SMTPRecipientsRefused as e:
        log_error(
            f"SMTP recipients refused: The server rejected the following recipients: {e}"
        )
    except smtplib.SMTPException as e:
        log_error(f"An SMTP error occurred: {e}")
    except Exception as e:
        log_error(f"An unexpected error occurred while sending email: {e}")

    return False


def send_notification(
    subject: str,
    description: str,
    emails: list[str],
    reading_settings: dict | None = None,
    use_html: bool = False,
) -> bool:
    """
    Send notification email with optional reading settings styling.

    Args:
        subject: Email subject
        description: Email body content
        emails: List of recipient email addresses
        reading_settings: Optional user reading settings for styling
        use_html: Whether to send as HTML email

    Returns:
        True if successful, False otherwise
    """
    try:
        result = send_mail(subject, description, emails, reading_settings, use_html)
    except Exception as e:
        log_error(e)
        return False
    else:
        return result
