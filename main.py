import os, subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
MAX_SEND = 45 * 1024 * 1024
CHANNEL = "@Y_EMEN21s"
CHANNEL_LINK = "https://t.me/Y_EMEN21s"

async def check_sub(user_id, context):
    try:
        m = await context.bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

async def send_sub_msg(update):
    keyboard = [
        [InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ تحققت، اشتركت", callback_data="check_sub")]
    ]
    text = "👋 أهلاً بك في بوت ضغط الفيديو!\n\n⚠️ عشان تستخدم البوت، لازم تشترك في قناتنا أولاً.\n\nاشترك وبعدين اضغط تحققت 👇"
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_sub(update.effective_user.id, context):
        await send_sub_msg(update)
        return
    await update.message.reply_text("أهلاً بك 😍 أرسل الفيديو عشان أضغطه لك\n720p • 480p • 360p • 240p • 144p • 96p • 64p • MP3")

async def on_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_sub(update.effective_user.id, context):
        await send_sub_msg(update)
        return
    video = update.message.video or update.message.document
    if not video:
        return
    size_mb = (video.file_size or 0) / 1024 / 1024
    context.user_data['file_id'] = video.file_id
    keyboard = [
        [InlineKeyboardButton("720p عالي", callback_data="720p"), InlineKeyboardButton("480p متوسط", callback_data="480p")],
        [InlineKeyboardButton("360p", callback_data="360p"), InlineKeyboardButton("240p", callback_data="240p")],
        [InlineKeyboardButton("144p", callback_data="144p"), InlineKeyboardButton("96p", callback_data="96p")],
        [InlineKeyboardButton("64p", callback_data="64p"), InlineKeyboardButton("🎵 MP3 صوت فقط", callback_data="mp3")],
    ]
    await update.message.reply_text(f"📹 وصل الفيديو ({size_mb:.1f} MB)\nاختار الجودة 👇", reply_markup=InlineKeyboardMarkup(keyboard))

async def on_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_sub":
        if await check_sub(query.from_user.id, context):
            await query.edit_message_text("✅ تم التحقق! أهلاً بك 😍\nأرسل الفيديو الآن")
        else:
            await query.answer("❌ عادك ما اشتركت! اشترك أولاً", show_alert=True)
        return
    if not await check_sub(query.from_user.id, context):
        await send_sub_msg(update)
        return

    quality = query.data
    file_id = context.user_data.get('file_id')
    if not file_id:
        await query.edit_message_text("❌ أرسل الفيديو من جديد")
        return

    await query.edit_message_text(f"⏳ جاري الضغط بجودة {quality} ... انتظر شوي")
    try:
        tg_file = await context.bot.get_file(file_id)
        await tg_file.download_to_drive("input.mp4")
        presets = {
            "720p": ["-vf", "scale=-2:720", "-crf", "28"],
            "480p": ["-vf", "scale=-2:480", "-crf", "30"],
            "360p": ["-vf", "scale=-2:360", "-crf", "32"],
            "240p": ["-vf", "scale=-2:240", "-crf", "34"],
            "144p": ["-vf", "scale=-2:144", "-crf", "36"],
            "96p": ["-vf", "scale=-2:96", "-crf", "38"],
            "64p": ["-vf", "scale=-2:64", "-crf", "40"],
        }
        if quality == "mp3":
            out = "output.mp3"
            cmd = ["ffmpeg", "-y", "-i", "input.mp4", "-vn", "-c:a", "libmp3lame", "-q:a", "4", out]
        else:
            out = "output.mp4"
            cmd = ["ffmpeg", "-y", "-i", "input.mp4"] + presets[quality] + ["-preset", "veryfast", "-c:a", "aac", "-b:a", "64k", out]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.exists(out) or os.path.getsize(out) == 0:
            await query.message.reply_text("❌ فشل الضغط، جرب فيديو ثاني")
            return

        if os.path.getsize(out) > MAX_SEND:
            await query.message.reply_text("❌ الفيديو بعد الضغط ما زال كبير، جرب جودة أقل")
            return

        with open(out, "rb") as f:
            if quality == "mp3":
                await query.message.reply_audio(audio=f, caption="✅ تم الضغط 🎵")
            else:
                await query.message.reply_video(video=f, caption=f"✅ تم الضغط بجودة {quality}")
    except Exception as e:
        await query.message.reply_text(f"❌ صار خطأ: {e}")
    finally:
        for tmp in ["input.mp4", "output.mp4", "output.mp3"]:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except: pass

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, on_video))
    app.add_handler(CallbackQueryHandler(on_quality))
    print("Bot started...")
    app.run_polling()
