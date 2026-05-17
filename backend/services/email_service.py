"""
Email service — sends transactional emails (OTP, etc.).

Provider preference order:
  1. Resend HTTPS API (if RESEND_API_KEY is set) — recommended.
  2. SMTP (if SMTP_USER + SMTP_PASS set) — Gmail App Password etc.
  3. Console log (dev only) — prints OTP so the flow keeps working
     when no provider is configured.

Configuration env vars
──────────────────────
  Resend:
    RESEND_API_KEY        Your API key from https://resend.com
    RESEND_FROM           "ResuMatch AI <noreply@yourdomain.com>"
                          (use 'onboarding@resend.dev' for testing without
                          a verified domain — Resend allows it only to the
                          account owner's email)

  SMTP (fallback):
    SMTP_HOST             default smtp.gmail.com
    SMTP_PORT             default 587
    SMTP_USER             Gmail address
    SMTP_PASS             Gmail App Password
    SMTP_FROM             optional From header
    SMTP_USE_SSL          "true" to use SMTP_SSL (port 465)
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────
def _resend_config():
    return {
        "api_key": os.getenv("RESEND_API_KEY"),
        "from_addr": os.getenv("RESEND_FROM") or "onboarding@resend.dev",
    }


def _smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASS"),
        "from_addr": os.getenv("SMTP_FROM") or os.getenv("SMTP_USER"),
        "use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() == "true",
    }


def _is_resend_configured() -> bool:
    return bool(_resend_config()["api_key"])


def _is_smtp_configured() -> bool:
    cfg = _smtp_config()
    return bool(cfg["user"] and cfg["password"])


def is_email_configured() -> bool:
    """True when any real provider (Resend or SMTP) is configured."""
    return _is_resend_configured() or _is_smtp_configured()


# ─────────────────────────────────────────────────────────────────────────────
# Templates
# ─────────────────────────────────────────────────────────────────────────────
def _otp_subject(otp: str) -> str:
    return f"ResuMatch AI — Your password reset code: {otp}"


def _otp_plain(otp: str, ttl_minutes: int) -> str:
    return (
        f"Your ResuMatch AI password reset code is: {otp}\n\n"
        f"This code expires in {ttl_minutes} minutes. "
        f"If you didn't request a password reset, you can safely ignore this email.\n"
    )


def _otp_html(otp: str, ttl_minutes: int) -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f8fafc; padding:24px;">
        <div style="max-width:520px; margin:0 auto; background:#ffffff; border-radius:14px;
                    border:1px solid #e2e8f0; padding:32px;">
          <h2 style="color:#0f172a; margin:0 0 4px 0;">Reset your password</h2>
          <p style="color:#64748b; margin:0 0 20px 0;">
            Use the verification code below to continue.
          </p>
          <div style="background:#eef2ff; color:#4338ca; font-size:32px; font-weight:700;
                      letter-spacing:8px; text-align:center; padding:18px; border-radius:10px;
                      font-family: 'Courier New', monospace;">
            {otp}
          </div>
          <p style="color:#475569; margin:20px 0 0 0; font-size:14px;">
            This code will expire in <b>{ttl_minutes} minutes</b>. If you didn't request this,
            you can safely ignore this email.
          </p>
          <hr style="border:none; border-top:1px solid #e2e8f0; margin:24px 0;" />
          <p style="color:#94a3b8; font-size:12px; margin:0;">
            ResuMatch AI &middot; Automated message, please do not reply.
          </p>
        </div>
      </body>
    </html>
    """


# ─────────────────────────────────────────────────────────────────────────────
# Resend (HTTPS API)
# ─────────────────────────────────────────────────────────────────────────────
def _send_via_resend(to_email: str, otp: str, ttl_minutes: int) -> bool:
    cfg = _resend_config()
    payload = {
        "from": cfg["from_addr"],
        "to": [to_email],
        "subject": _otp_subject(otp),
        "html": _otp_html(otp, ttl_minutes),
        "text": _otp_plain(otp, ttl_minutes),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        RESEND_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=15) as resp:
            status = resp.status
            data = resp.read().decode("utf-8", errors="replace")
            if 200 <= status < 300:
                logger.info("Resend: OTP email queued for %s", to_email)
                return True
            logger.error("Resend: unexpected status %s — %s", status, data)
            return False
    except HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = ""
        logger.error("Resend: HTTPError %s — %s", e.code, err_body)
        return False
    except URLError as e:
        logger.error("Resend: network error — %s", e)
        return False
    except Exception:
        logger.exception("Resend: unexpected failure sending to %s", to_email)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# SMTP (fallback)
# ─────────────────────────────────────────────────────────────────────────────
def _build_smtp_message(to_email: str, otp: str, from_addr: str, ttl_minutes: int) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = _otp_subject(otp)
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(_otp_plain(otp, ttl_minutes))
    msg.add_alternative(_otp_html(otp, ttl_minutes), subtype="html")
    return msg


def _send_via_smtp(to_email: str, otp: str, ttl_minutes: int) -> bool:
    cfg = _smtp_config()
    msg = _build_smtp_message(to_email, otp, cfg["from_addr"], ttl_minutes)
    try:
        if cfg["use_ssl"]:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx, timeout=15) as smtp:
                smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(cfg["user"], cfg["password"])
                smtp.send_message(msg)
        logger.info("SMTP: OTP email sent to %s", to_email)
        return True
    except Exception:
        logger.exception("SMTP: failed to send OTP to %s", to_email)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
def send_otp_email(to_email: str, otp: str, ttl_minutes: int = 10) -> bool:
    """
    Send a password-reset OTP email. Returns True on successful delivery.

    If no provider is configured, the OTP is logged to the backend console
    so development can continue.
    """
    if _is_resend_configured():
        if _send_via_resend(to_email, otp, ttl_minutes):
            return True
        # Resend failed — try SMTP if available before giving up
        logger.warning("Resend failed; attempting SMTP fallback if configured.")

    if _is_smtp_configured():
        if _send_via_smtp(to_email, otp, ttl_minutes):
            return True

    if not is_email_configured():
        logger.warning(
            "No email provider configured (set RESEND_API_KEY or SMTP_USER/SMTP_PASS). "
            "Logging OTP to console for development."
        )
    else:
        logger.warning("All configured providers failed. Logging OTP to console as fallback.")

    logger.info("[DEV] OTP for %s = %s (expires in %d min)", to_email, otp, ttl_minutes)
    return False
