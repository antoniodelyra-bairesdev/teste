from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import smtplib

from ehp import utils
from ehp.config import settings
from ehp.utils import constants as const
from ehp.utils.base import base64_encrypt, log_error


def send_txt_mail(subject: str, body: str, recipients: str) -> None:
    if subject and body and recipients:
        msg = MIMEText(body, "plain", _charset="UTF-8")

        msg["Subject"] = subject
        msg["From"] = formataddr(
            (str(Header(settings.APP_NAME, "utf-8")), settings.EMAIL_SENDER)
        )
        msg["To"] = recipients
        s = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        s.starttls()
        s.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        s.send_message(msg)
        s.quit()


def send_html_mail(
    subject: str,
    html_body: str,
    recipients: str,
    url_to: str,
    info_data: str,
) -> None:
    if subject and html_body and recipients:
        # Create message container - the correct MIME type is
        # multipart/alternative.
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr(
            (str(Header(settings.APP_NAME, "utf-8")), settings.EMAIL_SENDER)
        )
        msg["To"] = recipients

        code = (
            "[('email', '"
            + recipients
            + "'),"
            + " ('exp', '"
            + utils.str_datetime()
            + "')]"
        )

        html = f"""<!DOCTYPE html>
            <html>
            <head><title>{settings.APP_NAME}</title>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <style>
            .p_class {{
                font-family: Verdana, sans-serif;
                font-size:19px;
                font-style:normal;
                color:#333;
                margin-top:30px;
                text-align:justify;
                text-decoration:none;
            }}
            .img_class {{
                width:200px; height: auto; margin: 20px 0 20px 0;
            }}
            .h1_class {{
                font-family:Verdana, sans-serif;
                font-size:20px;
                font-weight:bold;
                background-color: #339933;
                color:#FFF;
                margin-top:50px;
                line-height: 65px;
                margin-bottom: 10px;
                text-align:center;
            }}
            .p_class2 {{
                font-family: Verdana, sans-serif;
                font-size:20px;
                color:#339933;
                line-height: 35px;
                margin-bottom: 10px;
                text-align:center;
            }}
            </style>
            </head>
            <body bgcolor="#FFFFFF" leftmargin="0" topmargin="0" marginwidth="0" marginheight="0">
            <table id="Table_01" width="850px" height="100%" border="0" cellpadding="0" cellspacing="0" align="center">
            <tr><td>
            <img src='{settings.APP_URL} static/images/logo.png' style="img_class">
            </td></tr>
            <tr><td style="width:100%; height:150px;">
            <p style="p_class">{html_body}</p></td></tr>"""

        if url_to == const.NOTI_ROUTE_INTERNAL:
            html += ""

        elif url_to == const.NOTI_ROUTE_UPDATE_PASSWORD:
            html = f"""{html}
                <tr><td>
                <a href='{settings.APP_URL}{url_to}?code={base64_encrypt(code).decode("utf-8")}'
                 target="_blank" style="text-decoration:none; color:#FFFFFF;">
                <h1 style="h1_class"><strong>Click here to get your new password</strong></h1>
                </a>
                </td></tr>
                <tr><td>
                <p style="p_class">Attention: this code expires in 30 min. After that you will need to request a new password.</p>
                </td></tr>"""

        elif url_to == const.NOTI_ROUTE_PASSWORD:
            html = f"""{html}
                <tr><td>
                <p style="p_class">
                Your temporary password is: <b> {info_data}</b>
                </p>
                </td></tr>"""

        elif url_to == const.NOTI_ROUTE_ACTIVATION:
            html = f"""{html}
                <tr><td>
                <a href='{settings.APP_URL}{url_to}?code={base64_encrypt(code.encode("utf-8")).decode("utf-8")}' target="_blank" style="text-decoration:none; color:#FFFFFF;">
                <h1 style="h1_class"><strong>Click here to activate your account</strong></h1>
                </a>
                </td></tr>
                <tr><td>
                <p style="p_class">Attention: this code expires in 30 min. After that you will need to request a new activation code.</p>
                </td></tr>"""

        html = f"""{html}
            <tr><td colspan="2" style="text-align: center;">
            <p class="text-muted text-center text-sm-left d-block d-sm-inline-block" style="p_class2">{settings.APP_NAME} available at Apple Store and Google Play.</p>
            <img src='{settings.APP_URL}static/images/bt-ios.png' style="margin: 20px;">
            <img src='{settings.APP_URL}static/images/bt-android.png' style="margin: 20px;">
            <br>
            </td></tr>
            <tr><td>
            <p style="p_class">
            Dúvidas? Entre em contato conosco nos canais<b>{settings.CONTACT_EMAIL}</b> / <b>{settings.CONTACT_PHONE}</b>.
            </p>
            <br/><br/></p></td></tr>
            <tr><td style="width: 100%; height: 85px; background-color: #000;">
            <img src='{settings.APP_URL}static/site/img/core-img/logo.png' style="width: 70px; display: block; margin-left: 46%; margin-right: 54%;" alt="">
            </td></tr>
            <tr>
            <td  style="width: 100%; height: 70px; ">
            <p class="text-muted text-center text-sm-left d-block d-sm-inline-block">Developed by MZ Unlimited LLC - www.mzunlimited.com</p>
            </td></tr>
            </table>
            </body>
            </html>"""

        msg.attach(MIMEText(html, "html"))
        s = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        s.starttls()
        s.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        s.send_message(msg)
        s.quit()


def send_notification(
    subject: str,
    description: str,
    emails: str,
    url_to: str,
    info_data: str,
) -> bool:
    try:
        send_html_mail(subject, description, emails, url_to, info_data)
    except Exception as e:
        log_error(e)
        return False
    return True
