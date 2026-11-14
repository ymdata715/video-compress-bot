import os, json, subprocess, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL = "@Y_EMEN21s"
ADMIN_ID = 8452001738
STATS_FILE = "stats.json"

logging.basicConfig(level=logging.INFO)

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"users": [], "total_videos": 0, "total_mp3": 0, "total_compress": 0}

def save_stats(data):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f)

stats = load_stats()

async def is_subscribed(context, user_id):
    try:
        m = await context.bot.get_chat_member(CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in stats["users"]:
        stats["users"].append(user_id)
        save_stats(stats)
    if not await is_subscribed(context, user_id):
        kb = [[InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{CHANNEL[1:]}")],
              [InlineKeyboardButton("✅ تحققت، اشتركت", callback_data="check_sub")]]
        await update.message.reply_text("عشان تستخدم البوت، لازم تشترك في قناتنا أولاً 👇", reply_markup=InlineKeyboardMarkup(kb))
        return
    await update.message.reply_text("🎬 أهلاً بك! ارسل أي فيديو، واختار الجودة.\n720p - 480p - 360p - 240p - 144p - 96p - 64p\nوأيضاً تقدر تحوله MP3 🎵")

async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_subscribed(context, q.from_user.id):
        await q.edit_message_text("✅ تم التحقق! ذلحين ارسل أي فيديو.")
    else:
        await q.answer("❌ عادك ما اشتركت، اشترك أولاً!", show_alert=True)

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ هذا الأمر للمشرف فقط.")
        return
    text = f"📊 احصائيات البوت:\n\n👥 عدد المستخدمين: {len(stats['users'])}\n🎬 إجمالي الفيديوهات: {stats['total_videos']}\n📹 إجمالي الضغط: {stats['total_compress']}\n🎵 إجمالي تحويل MP3: {stats['total_mp3']}"
    await update.message.reply_text(text)

async def on_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(context, user_id):
        await update.message.reply_text("❌ لازم تشترك في القناة أولاً، ارسل /start")
        return
    video = update.message.video or update.message.document
    if not video:
        return
    if video.file_size and video.file_size > 20*1024*1024:
        await update.message.reply_text("❌ هذا الفيديو كبير مرة، أكثر من 20 ميجا.")
        return
    context.user_data['file_id'] = video.file_id
    kb = [
        [InlineKeyboardButton("720p", callback_data="q_720"), InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("360p", callback_data="q_360"), InlineKeyboardButton("240p", callback_data="q_240")],
        [InlineKeyboardButton("144p", callback_data="q_144"), InlineKeyboardButton("96p", callback_data="q_96")],
        [InlineKeyboardButton("64p", callback_data="q_64")],
        [InlineKeyboardButton("🎵 تحويل MP3", callback_data="q_mp3")],
    ]
    await update.message.reply_text("اختار الجودة اللي تشتيها 👇", reply_markup=InlineKeyboardMarkup(kb))

async def on_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice = q.data.replace("q_", "")
    file_id = context.user_data.get('file_id')
    if not file_id:
        await q.edit_message_text("❌ ارسل الفيديو مرة ثانية.")
        return
    stats["total_videos"] += 1
    if choice == "mp3":
        stats["total_mp3"] += 1
    else:
        stats["total_compress"] += 1
    save_stats(stats)
    await q.edit_message_text(f"⏳ جاري الضغط بجودة {choice} ... انتظر شوي")
    try:
        file = await context.bot.get_file(file_id)
        input_path = f"in_{q.from_user.id}.mp4"
        await file.download_to_drive(input_path)
        if choice == "mp3":
            output_path = f"out_{q.from_user.id}.mp3"
            cmd = ["ffmpeg", "-y", "-i", input_path, "-vn", "-c:a", "libmp3lame", "-q:a", "4", output_path]
        else:
            output_path = f"out_{q.from_user.id}.mp4"
            h = {"720":720, "480":480, "360":360, "240":240, "144":144, "96":96, "64":64}.get(choice, 360)
            cmd = ["ffmpeg", "-y", "-i", input_path, "-vf", f"scale=-2:{h}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-c:a", "aac", output_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if choice == "mp3":
            await q.message.reply_audio(audio=open(output_path, "rb"))
        else:
            await q.message.reply_video(video=open(output_path, "rb"))
        await q.edit_message_text("✅ تم! ارسل فيديو ثاني لو تشتي.")
        for p in [input_path, output_path]:
            if os.path.exists(p): os.remove(p)
    except Exception as e:
        await q.edit_message_text(f"❌ صار خطأ: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", my_stats))
    app.add_handler(CallbackQueryHandler(check_sub, pattern="check_sub"))
    app.add_handler(CallbackQueryHandler(on_quality, pattern="^q_"))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.Document.MIME_TYPE("video/mp4"), on_video))
    app.run_polling()

if __name__ == "__main__":
    main()
