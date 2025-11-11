"""Mock SMTP Server for Email Testing

Provides a mock SMTP server that captures emails for verification in tests
without actually sending them.

Usage:
    >>> smtp = MockSMTPServer()
    >>> smtp.start()
    >>> capture = smtp.get_capture()

    # Send email in test
    >>> capture.send_email("from@test.com", "to@test.com", "Subject", "Body")

    # Verify in test
    >>> emails = capture.get_sent_emails()
    >>> assert len(emails) == 1
    >>> assert emails[0]["subject"] == "Subject"

    >>> smtp.stop()
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any


class MockEmailCapture:
    """Captures emails sent during tests for verification."""

    def __init__(self):
        """Initialize email capture."""
        self._emails: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def send_email(
        self,
        from_addr: str,
        to_addr: str,
        subject: str,
        body: str,
        html: str | None = None,
        cc: list[str | None] = None,
        bcc: list[str | None] = None,
    ):
        """Capture an email without actually sending it.

        Args:
            from_addr: Sender email address
            to_addr: Recipient email address
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
            cc: Optional CC recipients
            bcc: Optional BCC recipients
        """
        with self._lock:
            email = {
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "body": body,
                "html": html,
                "cc": cc or [],
                "bcc": bcc or [],
                "timestamp": datetime.now(UTC).isoformat(),
                "sent": True,
            }
            self._emails.append(email)

    def get_sent_emails(self, to_addr: str | None = None) -> list[dict[str, Any]]:
        """Get all captured emails.

        Args:
            to_addr: Optional filter by recipient

        Returns:
            List of captured email dictionaries
        """
        with self._lock:
            if to_addr:
                return [e for e in self._emails if e["to"] == to_addr]
            return list(self._emails)

    def get_last_email(self) -> dict[str, Any | None]:
        """Get the most recently captured email.

        Returns:
            Last email dictionary or None if no emails
        """
        with self._lock:
            return self._emails[-1] if self._emails else None

    def clear(self):
        """Clear all captured emails."""
        with self._lock:
            self._emails.clear()

    def count(self) -> int:
        """Get the number of captured emails.

        Returns:
            Number of emails
        """
        with self._lock:
            return len(self._emails)


class MockSMTPServer:
    """Mock SMTP server for email testing."""

    def __init__(self, host: str = "localhost", port: int = 1025):
        """Initialize mock SMTP server.

        Args:
            host: Server host
            port: Server port
        """
        self.host = host
        self.port = port
        self._capture = MockEmailCapture()
        self._running = False

    def start(self):
        """Start the mock SMTP server."""
        self._running = True
        print(f"Mock SMTP server started at {self.host}:{self.port}")

    def stop(self):
        """Stop the mock SMTP server."""
        self._running = False
        self._capture.clear()
        print("Mock SMTP server stopped")

    def get_capture(self) -> MockEmailCapture:
        """Get the email capture instance.

        Returns:
            Email capture instance
        """
        return self._capture

    def is_running(self) -> bool:
        """Check if the server is running.

        Returns:
            True if running, False otherwise
        """
        return self._running
