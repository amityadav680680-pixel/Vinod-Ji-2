"""Telegram bot: apna DB daalo, device search se nikal aaye."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Document, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.db import DeviceDB, format_device

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("device-bot")

DB_PATH = os.getenv("DATABASE_PATH", "data/devices.db")
db = DeviceDB(DB_PATH)

HELP_TEXT = """
📱 *Device DB Bot*

Apna device database yahan daalo — search karte hi device aa jayega.

*Commands:*
/start — bot shuru
/help — yeh message
/a `deviceid` — ID / serial / IMEI se device lao
/add `Name | Model | Serial | IMEI | Phone | Notes`
/list — saari devices
/find `query` — naam / serial / IMEI / phone se search
/count — kitni devices hain
/del `id` — device delete
/clear — apni saari devices wipe
/sample — demo data load

*DB import:*
CSV ya JSON file seedha chat mein bhej do.
Columns: `name,model,serial,imei,phone,notes`

*Example:*
`/a 1`
`/a SN-IPHONE-001`
`/add iPhone 14 | Apple | SN123 | 356789012345678 | 9876543210 | Ghar wala`
`/find iPhone`
""".strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Namaste! 👋\nApna device DB yahan daalo — /find se device aa jayega.\n\n"
        + HELP_TEXT,
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def a_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /a <deviceid> — seedha device details dikhao. """
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text(
            "Usage: /a <deviceid>\nExample: /a 1  ya  /a SN-IPHONE-001"
        )
        return
    device_id = " ".join(context.args).strip()
    row = db.get_by_device_id(chat_id, device_id)
    if row is None:
        await update.message.reply_text(f"❌ Device nahi mili: `{device_id}`", parse_mode="Markdown")
        return
    await update.message.reply_text(
        f"📱 *Device mil gayi:*\n\n{format_device(row)}",
        parse_mode="Markdown",
    )


async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    raw = " ".join(context.args).strip() if context.args else ""
    if not raw:
        await update.message.reply_text(
            "Usage:\n/add Name | Model | Serial | IMEI | Phone | Notes"
        )
        return

    parts = [p.strip() for p in raw.split("|")]
    while len(parts) < 6:
        parts.append("")
    name, model, serial, imei, phone, notes = parts[:6]
    if not name:
        await update.message.reply_text("Device ka naam zaroori hai.")
        return

    device_id = db.add_device(chat_id, name, model, serial, imei, phone, notes)
    await update.message.reply_text(f"✅ Device add ho gayi (#{device_id}): {name}")


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    rows = db.list_devices(chat_id)
    if not rows:
        await update.message.reply_text(
            "Abhi koi device nahi hai.\n/add se daalo ya CSV/JSON file bhejo."
        )
        return
    text = "📋 *Aapki devices:*\n\n" + "\n\n".join(format_device(r) for r in rows)
    await update.message.reply_text(text, parse_mode="Markdown")


async def find_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    query = " ".join(context.args).strip() if context.args else ""
    if not query:
        await update.message.reply_text("Usage: /find iPhone  ya  /find 356789")
        return
    rows = db.search(chat_id, query)
    if not rows:
        await update.message.reply_text(f"❌ '{query}' se koi device nahi mili.")
        return
    text = f"🔍 *'{query}' ke results:*\n\n" + "\n\n".join(format_device(r) for r in rows)
    await update.message.reply_text(text, parse_mode="Markdown")


async def count_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    n = db.count(chat_id)
    await update.message.reply_text(f"📦 Total devices: {n}")


async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Usage: /del 3")
        return
    try:
        device_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID number hona chahiye. Example: /del 3")
        return
    ok = db.delete_device(chat_id, device_id)
    if ok:
        await update.message.reply_text(f"🗑️ Device #{device_id} delete ho gayi.")
    else:
        await update.message.reply_text("Device nahi mili (galat ID?).")


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    n = db.clear_all(chat_id)
    await update.message.reply_text(f"🧹 {n} devices clear ho gayi.")


async def sample_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    sample = Path(__file__).resolve().parent.parent / "sample_data" / "devices.csv"
    if not sample.exists():
        await update.message.reply_text("Sample file missing hai.")
        return
    added = db.import_file(chat_id, sample)
    await update.message.reply_text(
        f"✅ {added} sample devices load ho gayi.\nAb /list ya /find iPhone try karo."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """CSV/JSON file chat mein bhejne par DB import."""
    chat_id = update.effective_chat.id
    doc: Document = update.message.document
    filename = (doc.file_name or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".json")):
        await update.message.reply_text("Sirf .csv ya .json file bhejo.")
        return

    tg_file = await doc.get_file()
    raw = await tg_file.download_as_bytearray()
    text = raw.decode("utf-8")

    try:
        if filename.endswith(".json"):
            added = db.import_json_text(chat_id, text)
        else:
            added = db.import_csv_text(chat_id, text)
    except Exception as exc:  # noqa: BLE001 - user-facing import errors
        await update.message.reply_text(f"Import fail: {exc}")
        return

    await update.message.reply_text(
        f"✅ DB import ho gaya — {added} devices add hui.\n/list ya /find se dekho."
    )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token.startswith("123456"):
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN set karo.\n"
            "1) Telegram pe @BotFather se /newbot\n"
            "2) Token copy karke .env mein daalo (dekh lo .env.example)\n"
            "3) phir: python -m bot.main"
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("a", a_cmd))
    app.add_handler(CommandHandler("add", add_cmd))
    app.add_handler(CommandHandler("list", list_cmd))
    app.add_handler(CommandHandler("find", find_cmd))
    app.add_handler(CommandHandler("search", find_cmd))
    app.add_handler(CommandHandler("count", count_cmd))
    app.add_handler(CommandHandler("del", del_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("sample", sample_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    logger.info("Bot starting… DB=%s", DB_PATH)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
