import os, subprocess, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
BOT_API_URL = os.getenv("BOT_API_URL", "https://api.telegram.org/bot")
ADMIN_ID = 8452001738
DB = "users.json"
MAX_SIZE = 2 * 1024 * 1024 * 1024

def load():
    try:
        d = json.load(open(DB))
        if "promo_link" not in d: d["promo_link"] = ""
        return d
    except: return {"users":{}, "channels":[], "prices":{"month":100, "year":500}, "promo_link":""}
def save(d): json.dump(d, open(DB,"w"))
data = load()

async def is_subscribed(context, user_id):
    # يرجع True اذا مشترك في كل القنوات، و False اذا مو مشترك
    for ch in data["channels"]:
        try:
            m = await context.bot.get_chat_member(ch, user_id)
            if m.status in ["left","kicked"]:
                return False, ch
        except:
            # اذا البوت مو مشرف في القناة، ما يقدر يتحقق، نعتبره مو مشترك عشان ما يتخطى
            return False, ch
    return True, None

async def send_sub_msg(message, ch):
    kb = [[InlineKeyboardButton(f"اشترك في {ch}", url=f"https://t.me/{ch.replace('@','')}")],[InlineKeyboardButton("✅ تحققت - اضغط هنا", callback_data="check_sub")]]
    await message.reply_text(f"⚠️ عذرا، عليك الاشتراك في القناة أولاً\n\n👉 اشترك في {ch} ثم اضغط تحققت", reply_markup=InlineKeyboardMarkup(kb))

def admin_kb():
    promo = data.get("promo_link") or "ما فيه"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ اضافة قناة اجباري", callback_data="adm_add_ch")],
        [InlineKeyboardButton("🗑 حذف قناة اجباري", callback_data="adm_del_ch")],
        [InlineKeyboardButton("📢 عرض القنوات", callback_data="adm_list_ch")],
        [InlineKeyboardButton(f"💰 تمويل قناتك: {promo[:25]}", callback_data="adm_set_promo")],
        [InlineKeyboardButton("🗑 حذف تمويل", callback_data="adm_del_promo")],
        [InlineKeyboardButton(f"💰 سعر شهر: {data['prices']['month']}", callback_data="adm_month")],
        [InlineKeyboardButton(f"💰 سعر سنة: {data['prices']['year']}", callback_data="adm_year")],
        [InlineKeyboardButton("📢 اذاعة للكل", callback_data="adm_broadcast")],
        [InlineKeyboardButton("👥 عدد المستخدمين", callback_data="adm_users")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    data["users"][uid] = {"name": update.effective_user.first_name}
    save(data)
    ok, ch = await is_subscribed(context, update.effective_user.id)
    if not ok:
        await send_sub_msg(update.message, ch); return
    kb = []
    if data.get("promo_link"):
        kb.append([InlineKeyboardButton("💰 تمويل قناتك", url=data["promo_link"])])
    kb.append([InlineKeyboardButton("⭐ اشتراك مميز", callback_data="premium")])
    await update.message.reply_text("🔥 بوت ضغط الفيديو - يصغّر الحجم ويحافظ على الجودة\n\nمن 1 ميجا إلى 2 جيجا\n\nارسل فيديو واختر الحجم اللي تريده", reply_markup=InlineKeyboardMarkup(kb))

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ انت مش مدير"); return
    await update.message.reply_text(f"🛠 لوحة المدير\n\n👥 المستخدمين: {len(data['users'])}\n📢 القنوات: {len(data['channels'])}\n💾 الحد: من 1 ميجا الى 2 جيجا\n\nاضغط على الزر اللي تريده:", reply_markup=admin_kb())

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # --- التحقق الجديد: حتى لو ارسل فيديو على طول ---
    ok, ch = await is_subscribed(context, update.effective_user.id)
    if not ok:
        await send_sub_msg(update.message, ch); return
    msg = update.message
    vid = msg.video or msg.document
    if not vid: return
    size_mb = vid.file_size / 1024 / 1024
    if vid.file_size > MAX_SIZE:
        await msg.reply_text(f"❌ الفيديو {size_mb:.0f} ميجا، أكبر من 2 جيجا"); return
    context.user_data["file_id"] = vid.file_id
    context.user_data["file_size"] = vid.file_size
    kb = [
        [InlineKeyboardButton("🎬 720p - جودة عالية", callback_data="c_720_high")],
        [InlineKeyboardButton("🎬 480p - متوازن", callback_data="c_480_mid")],
        [InlineKeyboardButton("📉 360p - حجم صغير", callback_data="c_360_small")],
        [InlineKeyboardButton("📉 240p - صغير جداً", callback_data="c_240_tiny")],
        [InlineKeyboardButton("📉 144p - أصغر شي", callback_data="c_144_mini")],
        [InlineKeyboardButton("📉 96p - أصغر شي على الإطلاق 🔥", callback_data="c_96_mini")],
        [InlineKeyboardButton("✂️ قص فيديو", callback_data="trim")],
        [InlineKeyboardButton("🔊 صوت - جودة عالية 128k", callback_data="a_128")],
        [InlineKeyboardButton("🔊 صوت - صغير 64k", callback_data="a_64")],
        [InlineKeyboardButton("🔊 صوت - أصغر شي 32k", callback_data="a_32")],
        [InlineKeyboardButton("⭐ اشتراك مميز", callback_data="premium")],
    ]
    if data.get("promo_link"):
        kb.append([InlineKeyboardButton("💰 تمويل قناتك", url=data["promo_link"])])
    await msg.reply_text(f"✅ استلمت: {size_mb:.1f} ميجا\n\nاختر كيف تريد تصغيره:", reply_markup=InlineKeyboardMarkup(kb))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    d = q.data
    if d == "check_sub":
        ok, ch = await is_subscribed(context, q.from_user.id)
        if not ok:
            await q.message.reply_text(f"⚠️ لسه ما اشتركت في {ch}\nاشترك بعدين اضغط تحققت"); return
        await q.message.reply_text("✅ تم التحقق! ذلحين ارسل فيديو"); return
    if d.startswith("adm_"):
        if q.from_user.id != ADMIN_ID:
            await q.message.reply_text("❌ انت مش مدير"); return
        if d == "adm_add_ch":
            context.user_data["waiting"] = "add_ch"
            await q.message.reply_text("➕ ارسل اسم القناة كذا:\n@اسم_القناة"); return
        if d == "adm_del_ch":
            if not data["channels"]:
                await q.message.reply_text("❌ ما فيه قنوات"); return
            kb = [[InlineKeyboardButton(f"🗑 حذف {ch}", callback_data=f"delch_{ch}")] for ch in data["channels"]]
            kb.append([InlineKeyboardButton("🔙 رجوع", callback_data="adm_back")])
            await q.message.reply_text("اختر القناة اللي تريد حذفها:", reply_markup=InlineKeyboardMarkup(kb)); return
        if d.startswith("delch_"):
            ch = d.replace("delch_","")
            if ch in data["channels"]: data["channels"].remove(ch); save(data)
            await q.message.reply_text(f"✅ تم حذف {ch}", reply_markup=admin_kb()); return
        if d == "adm_list_ch":
            txt = "\n".join(data["channels"]) or "ما فيه قنوات"
            await q.message.reply_text(f"📢 القنوات الاجبارية:\n{txt}", reply_markup=admin_kb()); return
        if d == "adm_set_promo":
            context.user_data["waiting"] = "promo"
            await q.message.reply_text("💰 ارسل رابط التمويل الجديد:\nhttps://t.me/قناتك"); return
        if d == "adm_del_promo":
            data["promo_link"] = ""; save(data)
            await q.message.reply_text("✅ تم حذف زر التمويل", reply_markup=admin_kb()); return
        if d == "adm_month":
            context.user_data["waiting"] = "month"
            await q.message.reply_text("💰 ارسل سعر الشهر الجديد، رقم فقط:"); return
        if d == "adm_year":
            context.user_data["waiting"] = "year"
            await q.message.reply_text("💰 ارسل سعر السنة الجديد، رقم فقط:"); return
        if d == "adm_broadcast":
            context.user_data["waiting"] = "broadcast"
            await q.message.reply_text("📢 ارسل رسالة الاذاعة ذلحين:"); return
        if d == "adm_users":
            await q.message.reply_text(f"👥 عدد المستخدمين: {len(data['users'])}", reply_markup=admin_kb()); return
        if d == "adm_back":
            await q.message.reply_text("🛠 لوحة المدير:", reply_markup=admin_kb()); return
    if d == "trim":
        context.user_data["waiting_trim"] = True
        await q.message.reply_text("✂️ ارسل وقت القص كذا:\n0:30-1:30"); return
    if d == "premium":
        kb = [[InlineKeyboardButton(f"شهر - {data['prices']['month']} ⭐", callback_data="buy_month")],[InlineKeyboardButton(f"سنة - {data['prices']['year']} ⭐", callback_data="buy_year")]]
        await q.message.reply_text("⭐ اختر الاشتراك:", reply_markup=InlineKeyboardMarkup(kb)); return
    VIDEO_PRESETS = {
        "c_720_high": ("720", "23", "128k", "medium"),
        "c_480_mid":  ("480", "26", "96k", "medium"),
        "c_360_small":("360", "28", "64k", "veryfast"),
        "c_240_tiny": ("240", "30", "48k", "veryfast"),
        "c_144_mini": ("144", "32", "32k", "veryfast"),
        "c_96_mini":  ("96", "35", "24k", "veryfast"),
    }
    AUDIO_PRESETS = {"a_128": "128k","a_64": "64k","a_32": "32k"}
    if d in VIDEO_PRESETS or d in AUDIO_PRESETS:
        # تحقق قبل الضغط كمان
        ok, ch = await is_subscribed(context, q.from_user.id)
        if not ok:
            await send_sub_msg(q.message, ch); return
        size_mb = context.user_data.get("file_size",0)/1024/1024
        await q.message.reply_text(f"⏳ جاري تحميل {size_mb:.1f} ميجا...")
        try:
            f = await context.bot.get_file(context.user_data["file_id"])
            in_path = f"in_{q.from_user.id}.mp4"
            await f.download_to_drive(in_path)
            real = os.path.getsize(in_path)/1024/1024
            if d in AUDIO_PRESETS:
                bitrate = AUDIO_PRESETS[d]
                out = f"out_{q.from_user.id}.mp3"
                subprocess.run(["ffmpeg","-y","-i",in_path,"-vn","-ac","1","-ar","22050","-b:a",bitrate,out], check=True)
                label = f"صوت {bitrate}"
            else:
                res, crf, abit, preset = VIDEO_PRESETS[d]
                out = f"out_{q.from_user.id}.mp4"
                subprocess.run(["ffmpeg","-y","-i",in_path,"-vf",f"scale=-2:{res}","-c:v","libx264","-crf",crf,"-preset",preset,"-c:a","aac","-b:a",abit,"-movflags","+faststart",out], check=True)
                label = f"{res}p"
            out_size = os.path.getsize(out)/1024/1024
            saved = 100 - (out_size/real*100) if real>0 else 0
            await q.message.reply_text(f"✅ تم التصغير! من {real:.1f} → {out_size:.1f} ميجا - وفرنا {saved:.0f}%")
            if d in AUDIO_PRESETS:
                await q.message.reply_audio(audio=open(out,"rb"), caption=f"✅ صوت {label} - من {real:.1f}MB → {out_size:.1f}MB")
            else:
                await q.message.reply_document(document=open(out,"rb"), caption=f"✅ فيديو {label} - من {real:.1f}MB → {out_size:.1f}MB 🔥")
            os.remove(in_path); os.remove(out)
        except Exception as e:
            await q.message.reply_text(f"❌ خطأ: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    if context.user_data.get("waiting_trim"):
        context.user_data["waiting_trim"] = False
        try:
            a,b = txt.split("-")
            def tosec(s):
                p = list(map(int,s.split(":")))
                return p[0]*60+p[1] if len(p)==2 else p[0]
            s1, s2 = tosec(a), tosec(b)
            await update.message.reply_text("⏳ جاري القص...")
            f = await context.bot.get_file(context.user_data["file_id"])
            in_path = f"in_{uid}.mp4"; await f.download_to_drive(in_path)
            out = f"trim_{uid}.mp4"
            subprocess.run(["ffmpeg","-y","-ss",str(s1),"-to",str(s2),"-i",in_path,"-c","copy",out], check=True)
            await update.message.reply_document(document=open(out,"rb"), caption="✅ تم القص")
            os.remove(in_path); os.remove(out)
        except: await update.message.reply_text("❌ اكتب كذا: 0:30-1:30")
        return
    if uid == ADMIN_ID and context.user_data.get("waiting"):
        w = context.user_data.pop("waiting")
        if w == "add_ch":
            if txt.startswith("@") and txt not in data["channels"]:
                data["channels"].append(txt); save(data)
                await update.message.reply_text(f"✅ تمت اضافة {txt} كقناة اجبارية", reply_markup=admin_kb())
            else: await update.message.reply_text("❌ ارسل كذا: @اسم_القناة")
            return
        if w == "promo":
            data["promo_link"] = txt; save(data)
            await update.message.reply_text(f"✅ تم حفظ رابط التمويل:\n{txt}", reply_markup=admin_kb()); return
        if w == "month":
            try: data["prices"]["month"] = int(txt); save(data); await update.message.reply_text("✅ تم تحديث سعر الشهر", reply_markup=admin_kb())
            except: await update.message.reply_text("❌ ارسل رقم فقط")
            return
        if w == "year":
            try: data["prices"]["year"] = int(txt); save(data); await update.message.reply_text("✅ تم تحديث سعر السنة", reply_markup=admin_kb())
            except: await update.message.reply_text("❌ ارسل رقم فقط")
            return
        if w == "broadcast":
            c=0
            for u in data["users"]:
                try: await context.bot.send_message(u, txt); c+=1
                except: pass
            await update.message.reply_text(f"✅ تمت الاذاعة لـ {c}", reply_markup=admin_kb()); return

async def post_init(app):
    await app.bot.set_my_commands([BotCommand("start","تشغيل البوت 🔥"), BotCommand("admin","لوحة المدير 🛠")])

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).base_url(BOT_API_URL).build()
    app.post_init = post_init
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot Started"); app.run_polling()
