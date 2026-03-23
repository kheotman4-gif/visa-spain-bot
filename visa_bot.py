import asyncio
import logging
import os
import json
import random
from datetime import datetime
from typing import Optional
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TARGET_URLS = ["https://visados.exteriores.gob.es/ConsularVirtual/es/inicio.html"]
AVAILABLE_KEYWORDS = ["disponible","cita disponible","fecha disponible","seleccione fecha","reservar","available","libre"]
UNAVAILABLE_KEYWORDS = ["no hay citas","no disponible","not available","sin citas disponibles","agotado"]
HEADERS = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"}
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
class BotState:
    def __init__(self):
        self.monitoring = False
        self.interval = 5
        self.check_count = 0
        self.slots_found = []
        self.last_check = None
        self.chat_ids = set()

state = BotState()

async def check_visa_website(url):
    try:
        await asyncio.sleep(random.uniform(1, 3))
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as response:
                if response.status != 200:
                    return {"success": False, "error": f"HTTP {response.status}", "url": url}
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text().lower()
                found_available = [kw for kw in AVAILABLE_KEYWORDS if kw in text]
                found_unavailable = [kw for kw in UNAVAILABLE_KEYWORDS if kw in text]
                slots = []
                is_available = len(found_available) > 0 and len(found_unavailable) == 0
                return {"success": True, "url": url, "is_available": is_available, "slots": slots, "found_available_keywords": found_available, "found_unavailable_keywords": found_unavailable}
    except Exception as e:
        return {"success": False, "error": str(e), "url": url}
async def monitoring_job(context):
    if not state.monitoring:
        return
    state.check_count += 1
    state.last_check = datetime.now()
    for url in TARGET_URLS:
        result = await check_visa_website(url)
        if not result["success"]:
            continue
        if result["is_available"]:
            state.slots_found.append({"url": url, "found_at": datetime.now().isoformat()})
            for chat_id in state.chat_ids:
                try:
                    keyboard = [[InlineKeyboardButton("فتح موقع السفارة", url=url)]]
                    await context.bot.send_message(chat_id=chat_id, text=f"🎉 موعد متاح!\n🔗 {url}\n⏰ {datetime.now().strftime('%H:%M:%S')}", reply_markup=InlineKeyboardMarkup(keyboard))
                except Exception as e:
                    logger.error(f"Error: {e}")
        else:
            logger.info(f"No slot - check #{state.check_count}")

async def cmd_start(update, context):
    chat_id = update.effective_chat.id
    state.chat_ids.add(chat_id)
    keyboard = [
        [InlineKeyboardButton("▶️ بدء المراقبة", callback_data="start"), InlineKeyboardButton("⏹ إيقاف", callback_data="stop")],
        [InlineKeyboardButton("🔍 تحقق الآن", callback_data="check"), InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
    ]
    await update.message.reply_text("🇪🇸 VisaTrack Spain Bot\nسأراقب مواعيد فيزا إسبانيا تلقائياً!", reply_markup=InlineKeyboardMarkup(keyboard))
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "start":
        state.monitoring = True
        state.chat_ids.add(query.message.chat_id)
        context.job_queue.run_repeating(monitoring_job, interval=state.interval*60, first=5, name="visa_monitor")
        await query.edit_message_text(f"✅ المراقبة بدأت! كل {state.interval} دقيقة 🔍")
    elif query.data == "stop":
        state.monitoring = False
        jobs = context.job_queue.get_jobs_by_name("visa_monitor")
        for job in jobs:
            job.schedule_removal()
        await query.edit_message_text("⏹ المراقبة أُوقفت")
    elif query.data == "check":
        await query.edit_message_text("🔍 جاري التحقق...")
        results = [await check_visa_website(url) for url in TARGET_URLS]
        state.check_count += 1
        r = results[0] if results else {}
        text = "🎉 موعد متاح!" if r.get("is_available") else f"📭 لا يوجد موعد\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        await query.edit_message_text(text)
    elif query.data == "stats":
        status = "🟢 نشطة" if state.monitoring else "🔴 متوقفة"
        await query.edit_message_text(f"📊 الإحصائيات\nالحالة: {status}\nالتحققات: {state.check_count}\nالفترة: {state.interval} دقيقة")

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN غير موجود!")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🇪🇸 VisaTrack Bot يعمل...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
