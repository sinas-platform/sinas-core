"""Email utility for sending OTP codes via SMTP."""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(email: str, otp_code: str) -> bool:
    """
    Send OTP code via SMTP.

    Falls back to console logging if SMTP is not configured.

    Args:
        email: Recipient email address
        otp_code: The OTP code to send

    Returns:
        True if email was sent or logged successfully
    """
    # Check if SMTP is configured
    if not all([settings.smtp_host, settings.smtp_user, settings.smtp_password, settings.smtp_domain]):
        logger.warning("SMTP not configured - printing OTP to console")
        print(f"\n{'='*60}")
        print(f"OTP Code for {email}: {otp_code}")
        print(f"{'='*60}\n")
        return True

    try:
        # Prepare email content
        from_email = f"login@{settings.smtp_domain}"
        subject = "Your Login Code"

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

        text_content = f"""
Your Login Code

Hello,

Your login verification code is: {otp_code}

This code will expire in {settings.otp_expire_minutes} minutes.

If you didn't request this code, please ignore this email.

Best regards,
SINAS Team
        """

        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = from_email
        message["To"] = email
        message["Subject"] = subject

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_content, "plain")
        part2 = MIMEText(html_content, "html")
        message.attach(part1)
        message.attach(part2)

        # Connect to SMTP server and send email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(from_email, email, message.as_string())

        logger.info(f"OTP email sent successfully to {email}")
        return True

    except Exception as e:
        logger.error(f"Error sending OTP email to {email}: {e}")
        # Fallback to console logging
        print(f"\n{'='*60}")
        print(f"Failed to send email. OTP Code for {email}: {otp_code}")
        print(f"{'='*60}\n")
        return True  # Still return True so auth flow continues
