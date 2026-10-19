"""Private development previews or STARTTLS SMTP; never log message bodies/links."""

import os
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


def deliver(settings, email: str, kind: str, token: str, *, mailbox=None):
    route = "verify-email" if kind == "verification" else "reset-password"
    # Fragment keeps one-time secrets out of HTTP access logs and referrers.
    link = f"{settings.frontend_url.rstrip('/')}/{route}#token={token}"
    if settings.email_adapter == "staging_sink":
        if (
            not settings.staging_demo
            or email not in settings.staging_synthetic_emails
            or mailbox is None
        ):
            raise ValueError("Synthetic mail sink is unavailable")
        mailbox.put(email, kind, link)
        return
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = email
    message["Subject"] = (
        "Verify your Atlas email" if kind == "verification" else "Reset your Atlas password"
    )
    message.set_content(
        f"Open this single-use link to continue:\n{link}\nIgnore this message if you did not request it.",
        # Local .eml previews are often read as raw text rather than by a MIME
        # reader. Keep their URL intact; SMTP retains its automatic encoding.
        cte="8bit" if settings.email_adapter == "preview" else None,
    )
    if settings.email_adapter == "preview":
        directory = Path(settings.mail_directory)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / f"{secrets.token_hex(16)}.eml"
        with os.fdopen(
            os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8"
        ) as file:
            file.write(message.as_string())
        return
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
