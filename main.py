import os, json, subprocess, logging, time, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, PreCheckoutQueryHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL = "@Y_EMEN21s" # قناتك الأساسية
ADMIN_ID = 8452001738
BASE_URL = os.environ.get("BOT_API_URL", "https://api.telegram.org/bot")
STATS_FILE = "stats.json"
logging.basicConfig(level=logging.INFO)
pending = {}
user_state = {}

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f: return json.load(f)
        except: pass
    return {"users": [], "videos": 0, "ads_shown": 0, "premium": {}, "daily": {}, "banned": [], "force_channels": ["@Y_EMEN21s"], "price_month": 50, "price_year": 300}
def save_stats(d):
    with open(STATS_FILE, "w") as f: json.dump(d, f)
stats = load_stats()

def is_premium(uid):
    return stats.get("premium", {}).get(str(uid), 0) > time.time()
def can_use(uid):
    if is_premium(uid): return True
    today = datetime.date.today().isoformat()
    return stats.get("daily", {}).get(str(uid), {}).get(today, 0) < 3
def add_use(uid):
    today = datetime.date.today().isoformat()
    stats.setdefault("daily", {}).setdefault(str(uid), {})[today] = stats["daily"][str(uid)].get(today, 0) + 1
    save_stats(stats)

# ===== فحص الاشتراك الإجباري =====
async def check_force_sub(context, uid):
    # يرجع قائمة القنوات اللي المستخدم مش مشترك فيها
    not_joined = []
    for ch in stats.get("force_channels", []):
        try:
            member = await context.bot.get_chat_member(ch, uid)
            if member.status in ["left", "kicked"]:
                not_joined.append(ch)
        except:
            not_joined.append(ch)
    return not_joined

async def send_force_msg(msg, not_joined):
    buttons = [[InlineKeyboardButton(f"📢 اشترك في {ch}", url=f"https://t.me/{ch.replace('@','')}")] for ch in not_joined]
    buttons.append([InlineKeyboardButton("✅ تحققت - اشتركت", callback_data="check_sub")])
    await msg.reply_text(
        "⛔ عشان تستخدم البوت لازم تشترك في القنوات هذي أولاً:\n\n"
        "اشترك وبعدين اضغط تحققت.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

VIDEO_QUALITIES = {
    "2160": {"label": "4K", "scale": "3840", "crf": "19", "audio": "192k", "preset": "medium"},
    "1440": {"label": "2K", "scale": "2560", "crf": "20", "audio": "192k", "preset": "medium"},
    "1080": {"label": "1080p", "scale": "1920", "crf": "20", "audio": "192k", "preset": "medium"},
    "720": {"label": "720p", "scale": "1280", "crf": "22", "audio": "128k", "preset": "medium"},
    "480": {"label": "480p", "scale": "854", "crf": "24", "audio": "96k", "preset": "veryfast"},
    "360": {"label": "360p", "scale": "640", "crf": "26", "audio": "64k", "preset": "veryfast"},
    "240": {"label": "240p - نت ضعيف", "scale": "426", "crf": "28", "audio": "48k", "preset": "veryfast"},
    "144": {"label": "144p - نت ضعيف جداً", "scale": "256", "crf": "30", "audio": "32k", "preset": "veryfast"},
    "auto": {"label": "🤖 ذكي", "scale": "1280", "crf": "23", "audio": "128k", "preset": "medium"},
}
AUDIO_QUALITIES = {
    "mp3_320": {"label": "MP3 320kbps", "ext": "mp3", "bitrate": "320k"},
    "mp3_128": {"label": "MP3 128kbps", "ext": "mp3", "bitrate": "128k"},
    "mp3_64": {"label": "MP3 64kbps", "ext": "mp3", "bitrate": "64k"},
    "voice": {"label": "رسالة صوتية", "ext": "ogg", "bitrate": "32k"},
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in stats.get("banned", []):
        await update.message.reply_text("❌ انت محظور."); return
    if uid not in stats["users"]:
        stats["users"].append(uid); save_stats(stats)
    # فحص الاشتراك الإجباري قبل أي شي
    not_joined = await check_force_sub(context, uid)
    if not_joined:
        await send_force_msg(update.message, not_joined); return
    prem = "⭐ مميز" if is_premium(uid) else "مجاني - 3 مرات في اليوم"
    await update.message.reply_text(f"أهلاً بك 🔥\nحسابك: {prem}\n\nأرسل فيديو واختار:\n🎬 ضغط\n✂️ قص\n🎵 صوت\n\nالبوت مجاني بدعم من {CHANNEL}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⭐ اشتراك مميز", callback_data="buy")],[InlineKeyboardButton("📢 قناتنا", url=f"https://t.me/{CHANNEL.replace('@','')}")]]))

# ===== لوحة تحكم المدير - كاملة من داخل البوت =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("🛠 لوحة تحكم المدير:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("⭐ قائمة المميزين", callback_data="admin_premium")],
            [InlineKeyboardButton("📢 إذاعة للكل", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🚫 حظر / ✅ فك حظر", callback_data="admin_ban")],
            [InlineKeyboardButton("🎁 إعطاء اشتراك مجاني", callback_data="admin_gift")],
            [InlineKeyboardButton("━━━━━━━━━━ 📢 قنوات الاشتراك الإجباري ━━━━━━━━━━", callback_data="noop")],
            [InlineKeyboardButton("➕ إضافة قناة إجبارية", callback_data="admin_add_channel")],
            [InlineKeyboardButton("📋 عرض القنوات الإجبارية", callback_data="admin_list_channels")],
            [InlineKeyboardButton("🗑 حذف قناة إجبارية", callback_data="admin_del_channel")],
            [InlineKeyboardButton("━━━━━━━━━━ 💰 أسعار النجوم ━━━━━━━━━━", callback_data="noop")],
            [InlineKeyboardButton(f"💰 سعر الشهر: {stats.get('price_month',50)} نجمة - تغيير", callback_data="admin_price_month")],
            [InlineKeyboardButton(f"💰 سعر السنة: {stats.get('price_year',300)} نجمة - تغيير", callback_data="admin_price_year")],
        ]))

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.from_user.id != ADMIN_ID: return
    if q.data == "admin_stats":
        prem_count = len([k for k,v in stats.get("premium", {}).items() if v > time.time()])
        await q.message.reply_text(f"📊 إحصائيات:\n👥 {len(stats['users'])}\n🎬 {stats['videos']}\n⭐ مميزين: {prem_count}\n📢 {stats['ads_shown']}\n🚫 {len(stats.get('banned',[]))}\n📢 قنوات إجبارية: {stats.get('force_channels',[])}")
    elif q.data == "admin_premium":
        lst = "\n".join([f"{k} - {datetime.datetime.fromtimestamp(v).strftime('%Y-%m-%d')}" for k,v in stats.get("premium", {}).items() if v > time.time()]) or "لا يوجد"
        await q.message.reply_text(f"⭐ المميزين:\n{lst}")
    elif q.data == "admin_broadcast":
        user_state[q.from_user.id] = "broadcast"; await q.message.reply_text("📢 ارسل رسالة الإذاعة:")
    elif q.data == "admin_ban":
        user_state[q.from_user.id] = "ban"; await q.message.reply_text("🚫 ارسل ايدي للحظر، أو للحذف ارسل: فك + الايدي\nمثال: 123456789\nمثال فك: فك 123456789")
    elif q.data == "admin_gift":
        user_state[q.from_user.id] = "gift"; await q.message.reply_text("🎁 ارسل: الايدي + الأيام\nمثال: 123456789 30")
    elif q.data == "admin_add_channel":
        user_state[q.from_user.id] = "add_channel"; await q.message.reply_text("➕ ارسل يوزر القناة اللي تشتي تضيفها إجباري:\nمثال: @Y_EMEN21s\n\nملاحظة: لازم تخلي البوت أدمن في القناة عشان يقدر يتحقق من الاشتراك.")
    elif q.data == "admin_list_channels":
        await q.message.reply_text(f"📋 القنوات الإجبارية الحالية:\n" + "\n".join(stats.get("force_channels", [])))
    elif q.data == "admin_del_channel":
        user_state[q.from_user.id] = "del_channel"; await q.message.reply_text("🗑 ارسل يوزر القناة اللي تشتي تحذفها:\nمثال: @Y_EMEN21s")
    elif q.data == "admin_price_month":
        user_state[q.from_user.id] = "price_month"; await q.message.reply_text(f"💰 السعر الحالي للشهر: {stats.get('price_month',50)} نجمة\nارسل السعر الجديد، مثال: 100")
    elif q.data == "admin_price_year":
        user_state[q.from_user.id] = "price_year"; await q.message.reply_text(f"💰 السعر الحالي للسنة: {stats.get('price_year',300)} نجمة\nارسل السعر الجديد، مثال: 500")

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; txt = (update.message.text or "").strip()
    if uid == ADMIN_ID and uid in user_state:
        st = user_state.pop(uid)
        if st == "broadcast":
            sent = 0
            for u in stats["users"]:
                try: await context.bot.send_message(u, txt); sent += 1
                except: pass
            await update.message.reply_text(f"✅ تمت الإذاعة لـ {sent}"); return
        if st == "ban":
            if txt.startswith("فك"):
                target = int(txt.replace("فك","").strip())
                if target in stats.get("banned", []): stats["banned"].remove(target); save_stats(stats)
                await update.message.reply_text(f"✅ فك حظر {target}"); return
            stats.setdefault("banned", []).append(int(txt)); save_stats(stats); await update.message.reply_text(f"✅ حظر {txt}"); return
        if st == "gift":
            parts = txt.split(); stats.setdefault("premium", {})[str(int(parts[0]))] = time.time() + int(parts[1])*86400; save_stats(stats); await update.message.reply_text(f"✅ اعطيت {parts[0]} اشتراك {parts[1]} يوم"); return
        if st == "add_channel":
            ch = txt if txt.startswith("@") else "@"+txt
            if ch not in stats["force_channels"]: stats["force_channels"].append(ch); save_stats(stats)
            await update.message.reply_text(f"✅ تمت إضافة {ch} كقناة إجبارية.\nذلحين أي عضو جديد ما يقدر يستخدم البوت إلا إذا اشترك فيها. هذا هو التمويل."); return
        if st == "del_channel":
            ch = txt if txt.startswith("@") else "@"+txt
            if ch in stats["force_channels"]: stats["force_channels"].remove(ch); save_stats(stats)
            await update.message.reply_text(f"✅ تم حذف {ch}"); return
        if st == "price_month":
            stats["price_month"] = int(txt); save_stats(stats); await update.message.reply_text(f"✅ سعر الشهر صار {txt} نجمة"); return
        if st == "price_year":
            stats["price_year"] = int(txt); save_stats(stats); await update.message.reply_text(f"✅ سعر السنة صار {txt} نجمة"); return
    if uid in user_state and user_state[uid] == "trim":
        try:
            a,b = txt.replace(" ","").split("-")
            pending[uid]["trim_start"] = a; pending[uid]["trim_end"] = b; user_state.pop(uid)
            await update.message.reply_text(f"✂️ بقص من {a} إلى {b}\nاختار الجودة:"); await show_quality_buttons(update.message, uid); return
        except: await update.message.reply_text("❌ ارسل كذا: 0:30-1:30"); return

async def show_quality_buttons(msg, uid):
    await msg.reply_text("اختار الجودة:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 4K ⭐ مميز", callback_data="v_2160")],
        [InlineKeyboardButton("💎 2K", callback_data="v_1440")],
        [InlineKeyboardButton("✅ 1080p", callback_data="v_1080")],
        [InlineKeyboardButton("📺 720p", callback_data="v_720")],
        [InlineKeyboardButton("📦 480p", callback_data="v_480")],
        [InlineKeyboardButton("📱 360p", callback_data="v_360")],
        [InlineKeyboardButton("🐢 240p", callback_data="v_240")],
        [InlineKeyboardButton("🐌 144p", callback_data="v_144")],
        [InlineKeyboardButton("🤖 ذكي", callback_data="v_auto")],
        [InlineKeyboardButton("🎵 MP3 / صوتي", callback_data="show_audio")],
    ]))

async def on_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message; uid = update.effective_user.id
    if uid in stats.get("banned", []): return
    # فحص إجباري قبل الضغط
    not_joined = await check_force_sub(context, uid)
    if not_joined:
        await send_force_msg(msg, not_joined); return
    if not can_use(uid):
        await msg.reply_text(f"❌ خلصت الـ 3 المجانية.\nاشترك: {stats.get('price_month',50)} نجمة / شهر", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⭐ اشتراك", callback_data="buy")]])); return
    file_obj = msg.video or msg.document
    if not file_obj: return
    pending[uid] = {"file_id": file_obj.file_id, "file_name": getattr(file_obj, "file_name", "video.mp4") or "video.mp4", "caption": msg.caption or "", "size": file_obj.file_size, "trim_start": None, "trim_end": None}
    await msg.reply_text(f"📥 تم استلام ({file_obj.file_size/(1024*1024):.1f} MB)\nاختار:", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 ضغط", callback_data="menu_quality")],
        [InlineKeyboardButton("✂️ قص", callback_data="menu_trim")],
        [InlineKeyboardButton("🎵 صوت", callback_data="show_audio")],
        [InlineKeyboardButton("⭐ اشتراك", callback_data="buy")],
    ]))

async def on_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); uid = q.from_user.id
    if q.data == "check_sub":
        not_joined = await check_force_sub(context, uid)
        if not not_joined:
            await q.message.reply_text("✅ تمام! اشتركت في الكل، ذلحين ارسل الفيديو.")
        else:
            await send_force_msg(q.message, not_joined)
        return
    if q.data == "menu_quality": await show_quality_buttons(q.message, uid); return
    if q.data == "menu_trim":
        user_state[uid] = "trim"; await q.message.reply_text("✂️ ارسل وقت القص: 0:30-1:30"); return
    if q.data == "show_audio":
        await q.message.reply_text("اختار الصوت:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎵 MP3 320", callback_data="a_mp3_320")],
            [InlineKeyboardButton("🎵 MP3 128", callback_data="a_mp3_128")],
            [InlineKeyboardButton("🎵 MP3 64", callback_data="a_mp3_64")],
            [InlineKeyboardButton("🎤 رسالة صوتية", callback_data="a_voice")],
        ])); return
    if q.data == "buy":
        pm = stats.get("price_month", 50); py = stats.get("price_year", 300)
        await q.message.reply_text(f"⭐ الاشتراك المميز:\n✅ غير محدود\n✅ 4K\n✅ قص غير محدود\n\nاختار:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⭐ شهر - {pm} نجمة", callback_data="buy_month")],
            [InlineKeyboardButton(f"⭐ سنة - {py} نجمة", callback_data="buy_year")],
        ])); return
    if q.data in ["buy_month", "buy_year"]:
        stars = stats.get("price_month", 50) if q.data == "buy_month" else stats.get("price_year", 300)
        days = 30 if q.data == "buy_month" else 365
        await context.bot.send_invoice(q.message.chat_id, title="اشتراك مميز", description=f"اشتراك {days} يوم", payload=f"premium_{days}", provider_token="", currency="XTR", prices=[LabeledPrice("اشتراك", stars)])
        return
    is_audio = q.data.startswith("a_"); key = q.data.replace("v_", "").replace("a_", "")
    if uid not in pending: return
    if key == "2160" and not is_premium(uid):
        await q.message.reply_text("❌ 4K للمميزين فقط.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⭐ اشتراك", callback_data="buy")]])); return
    data = pending[uid]
    try:
        tg_file = await context.bot.get_file(data["file_id"]); input_path = f"input_{uid}.mp4"; base_name = os.path.splitext(data["file_name"])[0]
        await tg_file.download_to_drive(input_path)
        trim_args = ["-ss", data["trim_start"], "-to", data["trim_end"]] if data.get("trim_start") else []
        await q.message.reply_text("⏳ جاري المعالجة...")
        if is_audio:
            aq = AUDIO_QUALITIES[key]; output_path = f"{base_name}.{aq['ext']}"
            cmd = ["ffmpeg", "-y"] + trim_args + ["-i", input_path, "-map_metadata", "0", "-metadata", f"title={base_name}", "-vn", "-c:a", "libopus" if aq['ext']=="ogg" else "libmp3lame", "-b:a", aq['bitrate'], output_path]
            label = aq['label']
        else:
            qq = VIDEO_QUALITIES[key]; output_path = f"{base_name}_{key}p.mp4"
            cmd = ["ffmpeg", "-y"] + trim_args + ["-i", input_path, "-map_metadata", "0", "-metadata", f"title={base_name}", "-vcodec", "libx264", "-crf", qq["crf"], "-preset", qq["preset"], "-vf", f"scale='min({qq['scale']},iw)':-2", "-acodec", "aac", "-b:a", qq["audio"], "-movflags", "+faststart", output_path]
            label = qq['label']
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.exists(output_path): await q.message.reply_text("❌ فشل."); return
        old_mb = data["size"] / (1024*1024); new_mb = os.path.getsize(output_path) / (1024*1024); saved = int((1 - new_mb/old_mb)*100) if old_mb>0 else 0
        add_use(uid); stats["videos"] += 1; stats["ads_shown"] += 1; save_stats(stats)
        trim_txt = f"\n✂️ مقصوص {data['trim_start']} - {data['trim_end']}" if data.get("trim_start") else ""
        await q.message.reply_text(f"✅ تم! {label}{trim_txt}\n📦 {old_mb:.1f} MB -> {new_mb:.1f} MB (وفرت {saved}%)\nمجاني بدعم من {CHANNEL}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 قناتنا", url=f"https://t.me/{CHANNEL.replace('@','')}")]]))
        final_caption = (data["caption"] + f"\n\nبواسطة {CHANNEL}") if data["caption"] else f"بواسطة {CHANNEL}"
        with open(output_path, "rb") as f:
            if is_audio:
                if key == "voice": await q.message.reply_voice(voice=f, caption=final_caption)
                else: await q.message.reply_audio(audio=f, filename=output_path, caption=final_caption, title=base_name)
            else: await q.message.reply_video(video=f, filename=output_path, caption=final_caption)
        for p in [input_path, output_path]:
            if os.path.exists(p): os.remove(p)
        del pending[uid]
    except Exception as e: logging.error(e); await q.message.reply_text(f"❌ خطأ: {e}")

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.pre_checkout_query.answer(ok=True)
async def success_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; payload = update.message.successful_payment.invoice_payload; days = 30 if "30" in payload else 365
    stats.setdefault("premium", {})[str(uid)] = time.time() + days*86400; save_stats(stats)
    await update.message.reply_text(f"🎉 صرت مميز {days} يوم ⭐")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).base_url(BASE_URL).base_file_url(BASE_URL + "/file").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, on_video))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(on_choice, pattern="^(menu_|show_|buy|v_|a_|check_sub|noop)"))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, success_payment))
    print("Bot Started"); app.run_polling()
