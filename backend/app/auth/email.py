"""Sending outgoing email for the auth flows (password reset).

Kept tiny on purpose: one ``send_email`` helper over stdlib ``smtplib``.
When ``SMTP_HOST`` is not configured we skip the network entirely and log
the message, so local development and tests work without a mail server.
"""

import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email, or log it when SMTP is not configured."""
    if not settings.SMTP_HOST:
        logger.info(
            "SMTP not configured; skipping email to %s. Subject: %s\n%s",
            to,
            subject,
            body,
        )
        return

    message = EmailMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    if settings.SMTP_USE_SSL:
        smtp: smtplib.SMTP = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
    else:
        smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
    with smtp:
        if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


def send_password_reset_email(to: str, reset_url: str) -> None:
    """Email a user the link to choose a new password."""
    subject = "Restablece tu contraseña de PrintForHelp"
    body = (
        "Hola,\n\n"
        "Recibimos una solicitud para restablecer tu contraseña. "
        "Abre este enlace para elegir una nueva:\n\n"
        f"{reset_url}\n\n"
        "El enlace vence en "
        f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutos. "
        "Si no fuiste tú, puedes ignorar este mensaje.\n\n"
        "— El equipo de PrintForHelp"
    )
    send_email(to, subject, body)
