import os, subprocess, math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
MAX_SEND = 45 * 1024 * 1024

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي أي فيديو ✅\nأي مدة، أي حجم، وأنا أضغطه لك")

async def on_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video or update.message.document
    if not video:
        return
    size_mb = (video.file_size or 0) / 1024 / 1024
    file = await video.get_file()
    await update.message.reply_text(f"تم استلام الفيديو ({size_mb:.1f} MB) ⬇️\nجاري تحميله...")
    await file.download_to_drive("input.mp4")
    keyboard = [
        [InlineKeyboardButton("720p عالي", callback_data="720")],
        [InlineKeyboardButton("480p متوسط", callback_data="480")],
        [InlineKeyboardButton("360p", callback_data="360")],
        [InlineKeyboardButton("240p ضعيف", callback_data="240")],
        [InlineKeyboardButton("144p ضعيف جدا", callback_data="144")],
        [InlineKeyboardButton("96p للنت البطيء 🐢", callback_data="96")],
        [InlineKeyboardButton("64p أصغر حجم ممكن ⚡", callback_data="64")],
        [InlineKeyboardButton("🎵 صوت فقط MP3", callback_data="audio")]
    ]
    await update.message.reply_text("اختار الجودة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_large_video(msg, path, caption):
    size = os.path.getsize(path)
    if size <= MAX_SEND:
        await msg.reply_video(video=open(path,"rb"), caption=caption)
        return
    await msg.reply_text(f"الفيديو كبير ({size/1024/1024:.1f} MB) بيتم تقسيمه لأجزاء... ✂️")
    probe = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1","output.mp4"], capture_output=True, text=True)
    try:
        duration = float(probe.stdout.strip())
    except:
        duration = 600
    parts = math.ceil(size / MAX_SEND)
    chunk = int(duration / parts) + 1
    for i in range(parts):
        start = i * chunk
        out = f"part{i}.mp4"
        subprocess.run(["ffmpeg","-y","-ss",str(start),"-i","output.mp4","-t",str(chunk),"-c","copy",out], check=True)
        await msg.reply_video(video=open(out,"rb"), caption=f"{caption} - جزء {i+1}/{parts}")
        os.remove(out)

async def on_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice = q.data
    if choice == "audio":
        msg = await q.message.reply_text("جاري تحويله لصوت... 🎵")
        try:
            subprocess.run(["ffmpeg","-y","-i","input.mp4","-vn","-acodec","libmp3lame","-q:a","5","output.mp3"], check=True)
            await q.message.reply_audio(audio=open("output.mp3","rb"), caption="تم التحويل لصوت ✅")
            os.remove("output.mp3")
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"فشل التحويل\n{e}")
        return
    crf_map = {"720":"23","480":"26","360":"28","240":"30","144":"32","96":"35","64":"38"}
    crf = crf_map[choice]
    preset = "ultrafast" if choice in ["96","64"] else "veryfast"
    msg = await q.message.reply_text(f"جاري الضغط {choice}p ... ⏳\nلو الفيديو طويل اصبر عليه شوي")
    try:
        subprocess.run(["ffmpeg","-y","-i","input.mp4","-vcodec","libx264","-crf",crf,"-preset",preset,"-vf",f"scale={choice}:-2","-acodec","aac","-b:a","64k","output.mp4"], check=True)
        await send_large_video(q.message, "output.mp4", f"تم الضغط {choice}p ✅")
        os.remove("output.mp4")
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"فشل الضغط\n{e}\nحاول جودة أوطى مثل 64p")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO | filters.Document.ALL, on_video))
    app.add_handler(CallbackQueryHandler(on_quality))
    print("Bot is running...")
    app.run_polling()
