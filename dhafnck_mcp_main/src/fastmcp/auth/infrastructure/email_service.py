"""
Email Service for Authentication Workflows

This module provides SMTP-based email sending functionality for authentication
features including user registration, password reset, and email verification.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import asyncio
import ssl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """SMTP Email configuration"""
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from: str
    smtp_from_name: str
    smtp_tls: bool = True
    smtp_secure: bool = False
    smtp_require_tls: bool = True
    smtp_auth: bool = True
    connection_timeout: int = 10000
    greeting_timeout: int = 5000
    socket_timeout: int = 10000


@dataclass
class EmailMessage:
    """Email message data"""
    to_email: str
    to_name: Optional[str] = None
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    template: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


@dataclass
class EmailResult:
    """Result of email sending operation"""
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    recipient: Optional[str] = None


class TokenManager:
    """Manages email verification and password reset tokens"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_verification_token(email: str, token_type: str = "verification") -> Dict[str, Any]:
        """Generate email verification token with metadata"""
        token = TokenManager.generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry
        
        # Create a hash for validation
        token_hash = hashlib.sha256(f"{email}:{token}:{token_type}".encode()).hexdigest()
        
        return {
            "token": token,
            "email": email,
            "type": token_type,
            "expires_at": expires_at,
            "hash": token_hash,
            "created_at": datetime.now(timezone.utc)
        }
    
    @staticmethod
    def validate_token(token: str, email: str, token_hash: str, token_type: str = "verification") -> bool:
        """Validate email verification token"""
        expected_hash = hashlib.sha256(f"{email}:{token}:{token_type}".encode()).hexdigest()
        return expected_hash == token_hash


class EmailTemplateEngine:
    """Handles email template rendering with Jinja2"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = os.path.join(
                os.path.dirname(__file__), 
                "..", "..", "..", "..", "templates", "email"
            )
        
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Create default templates if they don't exist
        self._ensure_default_templates()
    
    def _ensure_default_templates(self):
        """Create default email templates if they don't exist"""
        templates = {
            "verification.html": self._get_verification_template(),
            "password_reset.html": self._get_password_reset_template(),
            "password_changed.html": self._get_password_changed_template(),
            "welcome.html": self._get_welcome_template(),
            "base.html": self._get_base_template()
        }
        
        for template_name, template_content in templates.items():
            template_path = self.templates_dir / template_name
            if not template_path.exists():
                template_path.write_text(template_content, encoding='utf-8')
                logger.info(f"Created default email template: {template_name}")
    
    def render_template(self, template_name: str, **context) -> str:
        """Render email template with context data"""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise
    
    def _get_base_template(self) -> str:
        """Base email template"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title or "Oracle Server" }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 2px solid #007cba; padding-bottom: 20px; margin-bottom: 20px; }
        .logo { color: #007cba; font-size: 24px; font-weight: bold; }
        .content { margin: 20px 0; }
        .button { display: inline-block; background: #007cba; color: white !important; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .button:hover { background: #005a87; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin: 15px 0; }
        .code { font-family: monospace; background: #f8f9fa; padding: 8px 12px; border-radius: 4px; letter-spacing: 2px; font-size: 18px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{{ company_name or "Oracle Server" }}</div>
            {% if subtitle %}<p style="margin: 10px 0 0 0; color: #666;">{{ subtitle }}</p>{% endif %}
        </div>
        
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        
        <div class="footer">
            <p>This email was sent from {{ company_name or "Oracle Server" }}.</p>
            <p>If you didn't request this email, please ignore it or contact support.</p>
            <p>&copy; {{ current_year or "2025" }} {{ company_name or "Oracle Server" }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>"""
    
    def _get_verification_template(self) -> str:
        """Email verification template"""
        return """{% extends "base.html" %}

{% block content %}
<h2>Welcome to {{ company_name or "Oracle Server" }}!</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>Thank you for signing up! To complete your registration, please verify your email address by clicking the button below:</p>

<p style="text-align: center;">
    <a href="{{ verification_url }}" class="button">Verify Email Address</a>
</p>

<p>Or copy and paste this link into your browser:</p>
<p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{{ verification_url }}</p>

<div class="warning">
    <strong>Security Notice:</strong> This verification link will expire in 24 hours for security reasons.
</div>

<p>If you didn't create an account with us, please ignore this email.</p>

<p>Best regards,<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}"""
    
    def _get_password_reset_template(self) -> str:
        """Password reset template"""
        return """{% extends "base.html" %}

{% block content %}
<h2>Password Reset Request</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>We received a request to reset your password for your {{ company_name or "Oracle Server" }} account.</p>

<p>Click the button below to reset your password:</p>

<p style="text-align: center;">
    <a href="{{ reset_url }}" class="button">Reset Password</a>
</p>

<p>Or copy and paste this link into your browser:</p>
<p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{{ reset_url }}</p>

<div class="warning">
    <strong>Security Notice:</strong> This reset link will expire in 1 hour for security reasons.
</div>

<p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>

<p>Best regards,<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}"""
    
    def _get_password_changed_template(self) -> str:
        """Password changed confirmation template"""
        return """{% extends "base.html" %}

{% block content %}
<h2>Password Changed Successfully</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>This email confirms that your password for {{ company_name or "Oracle Server" }} has been successfully changed.</p>

<p><strong>Change Details:</strong></p>
<ul>
    <li>Date: {{ change_date or "Just now" }}</li>
    <li>IP Address: {{ ip_address or "Unknown" }}</li>
    <li>User Agent: {{ user_agent or "Unknown" }}</li>
</ul>

<div class="warning">
    <strong>Security Alert:</strong> If you didn't make this change, please contact our support team immediately.
</div>

<p>For your security, you may want to:</p>
<ul>
    <li>Review your recent account activity</li>
    <li>Enable two-factor authentication if available</li>
    <li>Use a unique, strong password</li>
</ul>

<p>Best regards,<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}"""
    
    def _get_welcome_template(self) -> str:
        """Welcome email template"""
        return """{% extends "base.html" %}

{% block content %}
<h2>Welcome to {{ company_name or "Oracle Server" }}!</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>Your email has been successfully verified and your account is now active!</p>

<p>Here are some things you can do to get started:</p>
<ul>
    <li>Complete your profile setup</li>
    <li>Explore the available features</li>
    <li>Join our community</li>
    <li>Contact support if you need help</li>
</ul>

<p style="text-align: center;">
    <a href="{{ dashboard_url or '#' }}" class="button">Get Started</a>
</p>

<p>If you have any questions, don't hesitate to reach out to our support team.</p>

<p>Welcome aboard!<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}"""


class SMTPEmailService:
    """SMTP-based email service for authentication workflows"""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """Initialize email service with configuration"""
        if config is None:
            config = self._load_config_from_env()
        
        self.config = config
        self.template_engine = EmailTemplateEngine()
        self.token_manager = TokenManager()
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"SMTP Email Service initialized for {self.config.smtp_host}:{self.config.smtp_port}")
    
    def _load_config_from_env(self) -> EmailConfig:
        """Load SMTP configuration from environment variables"""
        return EmailConfig(
            smtp_host=os.getenv("SMTP_HOST", "localhost"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_from=os.getenv("SMTP_FROM", "noreply@example.com"),
            smtp_from_name=os.getenv("SMTP_FROM_NAME", "Oracle Server"),
            smtp_tls=os.getenv("SMTP_TLS", "true").lower() in ("true", "1", "yes"),
            smtp_secure=os.getenv("SMTP_SECURE", "false").lower() in ("true", "1", "yes"),
            smtp_require_tls=os.getenv("SMTP_REQUIRE_TLS", "true").lower() in ("true", "1", "yes"),
            smtp_auth=os.getenv("SMTP_AUTH", "true").lower() in ("true", "1", "yes"),
            connection_timeout=int(os.getenv("SMTP_CONNECTION_TIMEOUT", "10000")),
            greeting_timeout=int(os.getenv("SMTP_GREETING_TIMEOUT", "5000")),
            socket_timeout=int(os.getenv("SMTP_SOCKET_TIMEOUT", "10000"))
        )
    
    def _validate_config(self):
        """Validate SMTP configuration"""
        if not self.config.smtp_host:
            raise ValueError("SMTP_HOST is required")
        if not self.config.smtp_username:
            raise ValueError("SMTP_USERNAME is required")
        if not self.config.smtp_password:
            raise ValueError("SMTP_PASSWORD is required")
        if not self.config.smtp_from:
            raise ValueError("SMTP_FROM is required")
    
    async def send_email(self, message: EmailMessage) -> EmailResult:
        """Send email message"""
        try:
            # Render template if specified
            if message.template and message.template_data:
                try:
                    message.html_body = self.template_engine.render_template(
                        message.template,
                        **message.template_data
                    )
                except Exception as e:
                    logger.error(f"Template rendering failed: {e}")
                    return EmailResult(
                        success=False,
                        error_message=f"Template rendering error: {str(e)}",
                        recipient=message.to_email
                    )
            
            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.config.smtp_from_name} <{self.config.smtp_from}>"
            msg["To"] = f"{message.to_name or ''} <{message.to_email}>".strip()
            msg["Subject"] = message.subject
            
            # Add text and HTML parts
            if message.text_body:
                text_part = MIMEText(message.text_body, "plain", "utf-8")
                msg.attach(text_part)
            
            if message.html_body:
                html_part = MIMEText(message.html_body, "html", "utf-8")
                msg.attach(html_part)
            
            # Add attachments if any
            if message.attachments:
                for attachment in message.attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            result = await self._send_smtp_message(msg, message.to_email)
            
            if result.success:
                logger.info(f"Email sent successfully to {message.to_email}")
            else:
                logger.error(f"Failed to send email to {message.to_email}: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            return EmailResult(
                success=False,
                error_message=str(e),
                recipient=message.to_email
            )
    
    async def _send_smtp_message(self, msg: MIMEMultipart, recipient: str) -> EmailResult:
        """Send MIME message via SMTP"""
        try:
            # Create SSL context
            # Check if this is a self-hosted instance (IP address in host)
            import re
            is_self_hosted = bool(re.search(r'\d+\.\d+\.\d+\.\d+', self.config.smtp_host))
            
            if is_self_hosted:
                # For self-hosted instances, disable certificate verification
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                logger.info(f"Using SSL context with verification disabled for self-hosted SMTP: {self.config.smtp_host}")
            else:
                # For cloud SMTP providers, use default SSL verification
                context = ssl.create_default_context()
            
            # Connect to SMTP server
            if self.config.smtp_secure:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    context=context,
                    timeout=self.config.connection_timeout / 1000
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self.config.connection_timeout / 1000
                )
                
                if self.config.smtp_tls or self.config.smtp_require_tls:
                    server.starttls(context=context)
            
            # Authenticate
            if self.config.smtp_auth:
                server.login(self.config.smtp_username, self.config.smtp_password)
            
            # Send message
            result = server.send_message(msg, to_addrs=[recipient])
            server.quit()
            
            return EmailResult(
                success=True,
                recipient=recipient,
                message_id=msg.get("Message-ID")
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"SMTP sending error: {error_msg}")
            
            # Provide user-friendly error messages
            if "authentication failed" in error_msg.lower():
                error_msg = "SMTP authentication failed. Please check credentials."
            elif "connection refused" in error_msg.lower():
                error_msg = "Cannot connect to SMTP server. Please check host and port."
            elif "timeout" in error_msg.lower():
                error_msg = "SMTP connection timeout. Please try again."
            
            return EmailResult(
                success=False,
                error_message=error_msg,
                recipient=recipient
            )
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to MIME message"""
        try:
            with open(attachment["path"], "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename= {attachment.get("filename", "attachment")}'
            )
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"Attachment error: {e}")
    
    # Authentication workflow methods
    
    async def send_verification_email(
        self,
        email: str,
        user_name: Optional[str] = None,
        verification_url: Optional[str] = None
    ) -> EmailResult:
        """Send email verification email"""
        # Generate verification token
        token_data = self.token_manager.generate_verification_token(email, "verification")
        
        # Build verification URL if not provided
        if not verification_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:3800")
            verification_url = f"{base_url}/auth/verify?token={token_data['token']}&email={email}"
        
        message = EmailMessage(
            to_email=email,
            to_name=user_name,
            subject="Verify your email address",
            template="verification.html",
            template_data={
                "user_name": user_name,
                "verification_url": verification_url,
                "company_name": os.getenv("SMTP_FROM_NAME", "Oracle Server"),
                "current_year": datetime.now().year
            }
        )
        
        return await self.send_email(message)
    
    async def send_password_reset_email(
        self,
        email: str,
        user_name: Optional[str] = None,
        reset_url: Optional[str] = None
    ) -> EmailResult:
        """Send password reset email"""
        # Generate password reset token
        token_data = self.token_manager.generate_verification_token(email, "password_reset")
        
        # Build reset URL if not provided
        if not reset_url:
            base_url = os.getenv("FRONTEND_URL", "http://localhost:3800")
            reset_url = f"{base_url}/auth/reset-password?token={token_data['token']}&email={email}"
        
        message = EmailMessage(
            to_email=email,
            to_name=user_name,
            subject="Reset your password",
            template="password_reset.html",
            template_data={
                "user_name": user_name,
                "reset_url": reset_url,
                "company_name": os.getenv("SMTP_FROM_NAME", "Oracle Server"),
                "current_year": datetime.now().year
            }
        )
        
        return await self.send_email(message)
    
    async def send_password_changed_email(
        self,
        email: str,
        user_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> EmailResult:
        """Send password changed confirmation email"""
        message = EmailMessage(
            to_email=email,
            to_name=user_name,
            subject="Password changed successfully",
            template="password_changed.html",
            template_data={
                "user_name": user_name,
                "change_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "company_name": os.getenv("SMTP_FROM_NAME", "Oracle Server"),
                "current_year": datetime.now().year
            }
        )
        
        return await self.send_email(message)
    
    async def send_welcome_email(
        self,
        email: str,
        user_name: Optional[str] = None,
        dashboard_url: Optional[str] = None
    ) -> EmailResult:
        """Send welcome email after successful verification"""
        if not dashboard_url:
            dashboard_url = os.getenv("FRONTEND_URL", "http://localhost:3800")
        
        message = EmailMessage(
            to_email=email,
            to_name=user_name,
            subject="Welcome! Your account is ready",
            template="welcome.html",
            template_data={
                "user_name": user_name,
                "dashboard_url": dashboard_url,
                "company_name": os.getenv("SMTP_FROM_NAME", "Oracle Server"),
                "current_year": datetime.now().year
            }
        )
        
        return await self.send_email(message)
    
    async def test_connection(self) -> EmailResult:
        """Test SMTP connection"""
        try:
            # Create SSL context
            # Check if this is a self-hosted instance (IP address in host)
            import re
            is_self_hosted = bool(re.search(r'\d+\.\d+\.\d+\.\d+', self.config.smtp_host))
            
            if is_self_hosted:
                # For self-hosted instances, disable certificate verification
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                logger.info(f"Using SSL context with verification disabled for self-hosted SMTP test: {self.config.smtp_host}")
            else:
                # For cloud SMTP providers, use default SSL verification
                context = ssl.create_default_context()
            
            # Test connection
            if self.config.smtp_secure:
                server = smtplib.SMTP_SSL(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    context=context,
                    timeout=self.config.connection_timeout / 1000
                )
            else:
                server = smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self.config.connection_timeout / 1000
                )
                
                if self.config.smtp_tls or self.config.smtp_require_tls:
                    server.starttls(context=context)
            
            # Test authentication
            if self.config.smtp_auth:
                server.login(self.config.smtp_username, self.config.smtp_password)
            
            server.quit()
            
            return EmailResult(
                success=True,
                message_id="connection_test",
                recipient="test"
            )
            
        except Exception as e:
            return EmailResult(
                success=False,
                error_message=str(e),
                recipient="test"
            )


# Global email service instance
_email_service: Optional[SMTPEmailService] = None


def get_email_service() -> SMTPEmailService:
    """Get global email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = SMTPEmailService()
    return _email_service


# Convenience functions for common operations
async def send_verification_email(email: str, user_name: Optional[str] = None) -> EmailResult:
    """Send verification email using global service"""
    service = get_email_service()
    return await service.send_verification_email(email, user_name)


async def send_password_reset_email(email: str, user_name: Optional[str] = None) -> EmailResult:
    """Send password reset email using global service"""
    service = get_email_service()
    return await service.send_password_reset_email(email, user_name)


async def send_password_changed_email(email: str, user_name: Optional[str] = None) -> EmailResult:
    """Send password changed email using global service"""
    service = get_email_service()
    return await service.send_password_changed_email(email, user_name)


async def send_welcome_email(email: str, user_name: Optional[str] = None) -> EmailResult:
    """Send welcome email using global service"""
    service = get_email_service()
    return await service.send_welcome_email(email, user_name)