import aiohttp
import requests

from .base import BaseEmailService
from .exc import EmailServiceException


class BrevoEmailService(BaseEmailService):
    def __init__(self, sender_name, sender_email, *, api_key: str):
        super().__init__(sender_name, sender_email)

        self._http_sess: aiohttp.ClientSession | None = None
        self._http_sess_sync: requests.Session | None = None
        self._url = "https://api.brevo.com/v3/smtp/email"
        self._headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json",
        }

    async def send_email(self, recipient: str, subject: str, body: str) -> None:
        self._ensure_open()

        if not recipient:
            raise ValueError("recipient is required")

        await self._send_via_brevo(recipient, subject, body)
        self._log_sent(recipient)

    async def _send_via_brevo(self, recipient: str, subject: str, body: str) -> None:
        """
        Uses Brevo SMTP API endpoint: POST https://api.brevo.com/v3/smtp/email
        Documentation: https://developers.brevo.com/
        """
        if self._http_sess is None or self._http_sess.closed:
            self._http_sess = aiohttp.ClientSession()

        payload = self._build_body(recipient, subject, body)

        rsp = await self._http_sess.post(self._url, json=payload, headers=self._headers)
        if rsp.status >= 400:
            text = await rsp.text()
            msg = f"Brevo API error: {rsp.status} - {text}"
            self._logger.error(msg)
            raise EmailServiceException(msg)

    async def close(self):
        """Gracefully close the internal HTTP session."""
        if self._closed:
            return

        self._closed = True
        if self._http_sess is not None and not self._http_sess.closed:
            await self._http_sess.close()

    def send_email_sync(self, recipient: str, subject: str, body: str) -> None:
        """
        Pure synchronous version of send_email().
        No asyncio used. Uses requests directly.
        """
        self._ensure_open()

        if not recipient:
            raise ValueError("recipient is required")

        self._send_via_brevo_sync(recipient, subject, body)
        self._log_sent(recipient)

    def _send_via_brevo_sync(self, recipient: str, subject: str, body: str) -> None:
        """Synchronous version using requests instead of aiohttp."""
        if self._http_sess_sync is None:
            self._http_sess_sync = requests.Session()

        payload = self._build_body(recipient, subject, body)

        rsp = self._http_sess_sync.post(
            self._url, json=payload, headers=self._headers, timeout=15
        )
        if rsp.status_code >= 400:
            msg = f"Brevo API error: {rsp.status_code} - {rsp.text}"
            self._logger.error(msg)
            raise EmailServiceException(msg)

    def close_sync(self):
        """
        No-op for synchronous mode.
        Included for interface consistency.
        """
        if self._closed:
            return

        self._closed = True

        if self._http_sess_sync is not None:
            self._http_sess_sync.close()

    def _build_body(self, recipient: str, subject: str, body: str) -> dict:
        return {
            "sender": {"name": self._sender_name, "email": self._sender_email},
            "to": [{"email": recipient}],
            "subject": subject,
            "textContent": body,
            "htmlContent": self._escape_html(body),
        }

    def _log_sent(self, recipient: str):
        msg = (
            f"Email sent (sync) via Brevo sender_name={self._sender_name}, "
            f"sender_email={self._sender_email}, recipient={recipient}"
        )
        self._logger.info(msg)
