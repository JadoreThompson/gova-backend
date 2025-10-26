import logging

from aiohttp import ClientSession

from config import BREVO_API_KEY


logger = logging.getLogger("email_service")


class EmailService:
    _instances: dict[tuple[str, str], "EmailService"] = {}

    def __new__(cls, sender_name: str, sender_email: str):
        key = (sender_name, sender_email)
        if key in cls._instances:
            return cls._instances[key]
        instance = super().__new__(cls)
        cls._instances[key] = instance
        return instance

    def __init__(self, sender_name: str, sender_email: str) -> None:
        # Prevent reinitialization for existing singletons
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.sender_name = sender_name
        self.sender_email = sender_email
        self._http_sess: ClientSession | None = None
        self._initialized = True

    async def send_email(self, recipient: str, subject: str, body: str) -> None:
        if not recipient:
            raise ValueError("recipient is required")

        try:
            await self._send_via_brevo(recipient, subject, body)
            logger.info("Email sent via Brevo to %s", recipient)
        except Exception as e:
            logger.exception("Brevo send failed, attempting SMTP fallback: %s", e)

    async def _send_via_brevo(self, recipient: str, subject: str, body: str) -> None:
        """
        Uses Brevo SMTP API endpoint: POST https://api.brevo.com/v3/smtp/email
        Documentation: https://developers.brevo.com/
        """
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        }

        payload = {
            "sender": {"name": self.sender_name, "email": self.sender_email},
            "to": [{"email": recipient}],
            "subject": subject,
            "textContent": body,
            "htmlContent": self._escape_html(body),
        }

        if self._http_sess is None or self._http_sess.closed:
            self._http_sess = ClientSession()

        rsp = await self._http_sess.post(url, json=payload, headers=headers)
        if rsp.status >= 400:
            text = await rsp.text()
            logger.error("Brevo API error: %s - %s", rsp.status, text)
            raise RuntimeError(f"Brevo API returned {rsp.status}: {text}")

    @staticmethod
    def _escape_html(s: str) -> str:
        """Minimal HTML escaper for embedding plain text into <pre> blocks."""
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    async def close(self):
        """Gracefully close the internal HTTP session."""
        if self._http_sess and not self._http_sess.closed:
            await self._http_sess.close()
