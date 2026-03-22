import asyncio, logging, os, json, random
from datetime import datetime
from typing import Optional
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
TARGET_URLS = ["https://visados.exteriores.gob.es/ConsularVirtual/es/inicio.html"]
AVAILABLE_KEYWORDS = ["disponible","cita disponible","fecha disponible","seleccione fecha","reservar","available","libre"]
UNAVAILABLE_KEYWORDS = ["no hay citas","no disponible","not available","sin citas disponibles","agotado"]
HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
