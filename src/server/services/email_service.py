import logging
import requests
from aiohttp import ClientSession
from config import BREVO_API_KEY


logger = logging.getLogger("email_service")
