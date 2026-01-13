"""Simple email utility for OTP authentication."""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def send_otp_email_async(db: AsyncSession, email: str, otp_code: str) -> bool:
    """
    Send OTP code via SMTP.
    Falls back to console logging if SMTP is not configured.

    Args:
        db: Database session (not used, kept for compatibility)
        email: Recipient email address
        otp_code: The OTP code to send

    Returns:
        True if email was sent or logged successfully
    """
    from app.core.config import settings

    # Fallback to console logging if SMTP not configured
    if not settings.smtp_host or not settings.smtp_domain:
        logger.warning("SMTP not configured. OTP code for console testing:")
        logger.warning(f"Email: {email}")
        logger.warning(f"OTP Code: {otp_code}")
        print(f"\n{'='*60}")
        print(f"OTP CODE FOR {email}: {otp_code}")
        print(f"{'='*60}\n")
        return True

    subject = "Your Login Code"
    from_email = f"login@{settings.smtp_domain}"

    # HTML content
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Your Login Code</h2>
        <p>Hello,</p>
        <p>Your login verification code is:</p>
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
            <h1 style="color: #007bff; font-size: 32px; margin: 0; letter-spacing: 8px;">{otp_code}</h1>
        </div>
        <p>This code will expire in {settings.otp_expire_minutes} minutes.</p>
        <p>If you didn't request this code, please ignore this email.</p>
        <p>Best regards,<br>SINAS Team</p>
    </div>
    """

    # Text content
    text_content = f"""
Your Login Code

Hello,

Your login verification code is: {otp_code}

This code will expire in {settings.otp_expire_minutes} minutes.

If you didn't request this code, please ignore this email.

Best regards,
SINAS Team
    """

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = email

        # Attach both text and HTML versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send via SMTP
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info(f"OTP email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        logger.warning(f"OTP code for console fallback: {otp_code}")
        print(f"\n{'='*60}")
        print(f"SMTP FAILED - OTP CODE FOR {email}: {otp_code}")
        print(f"{'='*60}\n")
        return True  # Return True anyway so authentication can proceed


__all__ = ['send_otp_email_async']
