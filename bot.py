"""
🎌 KageDub Anime Telegram Bot (Python 3 - aiogram 3.x)
Token: 8732171636:AAGc0HkdTpjKOlpVjplNeRpvSZBOZa-53EM
Kanal: -1003852596133 (@kagedub1)
Owner ID: 8318241400 (Faqat Owner VIP boshqara oladi!)
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
import aiohttp

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

# ==========================================
# 1. SOZLAMALAR (SIZNING MA'LUMOTLARINGIZ)
# ==========================================
BOT_TOKEN = "8732171636:AAGc0HkdTpjKOlpVjplNeRpvSZBOZa-53EM"
OWNER_ID = 8318241400
ADMIN_IDS = [8318241400]
CHANNEL_ID = "-1003852596133"
CHANNEL_USERNAME = "@kagedub1"
CHANNEL_INVITE = "https://t.me/kagedub1"
DB_FILE = "kagedub_db.json"

logging.basicConfig(level=logging.INFO)

# ==========================================
# 2. MA'LUMOTLAR BAZASI (JSON)
# ==========================================
DEFAULT_DB = {
    "users": {},
    "vip_users": {
        "8318241400": {"user_id": 8318241400, "expires_at": "Cheksiz (Owner)", "is_active": True}
    },
    "watchlists": {},
    "maintenance": False,
    "animes": [
        {
            "id": "anime_1",
            "title": "Kimetsu no Yaiba (Demon Slayer)",
            "genres": ["Action", "Fantasy", "Shounen"],
            "status_uz": "Tugatilgan",
            "score": 8.7,
            "poster_url": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&auto=format&fit=crop&q=80",
            "description": "Tanjiro singlisi Nezukoni iblisdan yana insonga aylantirish uchun Iblis Qotili bo'lish yo'liga qadam qo'yadi.",
            "episodes": [
                {"id": "ep1", "number": 1, "title": "1-qism", "url": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", "is_vip": False},
                {"id": "ep2", "number": 2, "title": "2-qism", "url": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", "is_vip": False},
                {"id": "ep3", "number": 3, "title": "3-qism [VIP Erta Premyera]", "url": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", "is_vip": True}
            ]
        },
        {
            "id": "anime_2",
            "title": "Solo Leveling (Yakka Darajalanuvchi)",
            "genres": ["Action", "Fantasy"],
            "status_uz": "Chiqmoqda",
            "score": 9.4,
            "poster_url": "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=600&auto=format&fit=crop&q=80",
            "description": "Eng zaif E-darajali ovchi Sung Jinwoo butun dunyodagi yagona darajalanuvchi ovchiga aylanadi.",
            "episodes": [
                {"id": "ep1", "number": 1, "title": "1-qism", "url": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", "is_vip": False},
                {"id": "ep2", "number": 2, "title": "2-qism [VIP Premyera]", "url": "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", "is_vip": True}
            ]
        }
    ]
}

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_DB
    return DEFAULT_DB

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Baza saqlashda xato: {e}")

db = load_db()

def is_vip(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    v = db.get("vip_users", {}).get(str(user_id))
    return bool(v and v.get("is_active"))

# ==========================================
# 3. ANILIST API QIDIRUV (GraphQL)
# ==========================================
async def search_anilist(query: str):
    gql = """
    query ($search: String) {
      Page (page: 1, perPage: 5) {
        media (search: $search, type: ANIME, sort: POPULARITY_DESC) {
          id
          title { romaji english }
          genres
          averageScore
          coverImage { large extraLarge }
          description(asHtml: false)
        }
      }
    }
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://graphql.anilist.co",
                json={"query": gql, "variables": {"search": query}},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as res:
                data = await res.json()
                return data.get("data", {}).get("Page", {}).get("media", [])
        except Exception as e:
            logging.error(f"AniList API error: {e}")
            return []

# ==========================================
# 4. FSM HOLATLARI
# ==========================================
class BotState(StatesGroup):
    waiting_search = State()

router = Router()

# ==========================================
# 5. MAJBURIY OBUNA TEKSHIRUVI (QOTMAYDI!)
# ==========================================
async def check_user_sub(bot: Bot, user_id: int) -> bool:
    if user_id == OWNER_ID or user_id in ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member", "restricted"]
    except TelegramBadRequest as e:
        logging.warning(f"Kanal a'zoligini tekshirishda ogohlantirish (Bot kanalda admin bo'lishi kerak): {e}")
        return True
    except Exception as e:
        logging.error(f"Xato: {e}")
        return True

def get_sub_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 KageDub Kanaliga Kirish", url=CHANNEL_INVITE)],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim (Tekshirish)", callback_data="check_sub")]
    ])

def get_main_keyboard(user_id: int):
    vip_status = is_vip(user_id)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Anime Qidirish", callback_data="menu_search"),
            InlineKeyboardButton(text="⭐ Sevimlilar", callback_data="menu_watchlist")
        ],
        [
            InlineKeyboardButton(text="🎲 Tasodifiy Anime", callback_data="menu_random"),
            InlineKeyboardButton(text="👑 VIP Holatim", callback_data="menu_vip")
        ],
        [
            InlineKeyboardButton(text="📢 KageDub Kanali (@kagedub1)", url=CHANNEL_INVITE)
        ]
    ])

# ==========================================
# 6. ASOSIY FOYDALANUVCHI HANDLERLARI
# ==========================================
@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    user = message.from_user
    db["users"][str(user.id)] = {"id": user.id, "name": user.full_name, "username": user.username}
    save_db(db)

    # Majburiy obunani tekshirish
    is_subbed = await check_user_sub(bot, user.id)
    if not is_subbed:
        text = (
            "👋 <b>Assalomu alaykum, aziz anime muxlisi!</b>\n\n"
            "🎌 Botdan to'liq foydalanish va eng yangi animelarni o'zbek tilida yuqori sifatda tomosha qilish uchun "
            "<b>KageDub</b> rasmiy kanaliga a'zo bo'ling:\n\n"
            "👇 <i>Kanalga a'zo bo'lgach 'A'zo bo'ldim' tugmasini bosing:</i>"
        )
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_sub_keyboard())
        return

    vip_badge = "👑 VIP A'zo" if is_vip(user.id) else "Oddiy Foydalanuvchi"
    text = (
        f"🎌 <b>Assalomu alaykum, {user.first_name}!</b>\n\n"
        f"⚡ <b>KageDub Official Bot</b> ga xush kelibsiz!\n"
        f"👑 Statusingiz: <b>{vip_badge}</b>\n\n"
        f"👇 <i>Kerakli bo'limni tanlang:</i>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(user.id))

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    is_subbed = await check_user_sub(bot, user_id)
    if not is_subbed:
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmadingiz! Iltimos obuna bo'ling.", show_alert=True)
        return

    await callback.answer("✅ Rahmat! Obunangiz tasdiqlandi.")
    vip_badge = "👑 VIP A'zo" if is_vip(user_id) else "Oddiy Foydalanuvchi"
    text = (
        f"🎉 <b>Obunangiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
        f"⚡ <b>KageDub Anime Bot</b>\n"
        f"👑 Statusingiz: <b>{vip_badge}</b>\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(user_id))

@router.callback_query(F.data == "menu_main")
async def cb_menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user_id = callback.from_user.id
    vip_badge = "👑 VIP A'zo" if is_vip(user_id) else "Oddiy Foydalanuvchi"
    text = (
        f"🎌 <b>KageDub Asosiy Menyu</b>\n\n"
        f"👑 Status: <b>{vip_badge}</b>\n\n"
        f"Kerakli bo'limni tanlang:"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=get_main_keyboard(user_id))

# VIP Holati
@router.callback_query(F.data == "menu_vip")
async def cb_menu_vip(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if is_vip(user_id):
        text = (
            "👑 <b>Sizning VIP Statusingiz: FAOL!</b>\n\n"
            "Siz barcha premyera va eksklyuziv 1080p qismlarni hech qanday cheklovlarsiz tomosha qilishingiz mumkin!"
        )
    else:
        text = (
            "👑 <b>Sizda hozircha VIP status mavjud emas.</b>\n\n"
            "VIP imtiyozlari:\n"
            "• Erta premyera qismlarni tomosha qilish\n"
            "• 1080p Full HD sifatda yuklab olish\n"
            "• Eksklyuziv animelar\n\n"
            "VIP obuna olish uchun kanal adminiga (@kagedub1) murojaat qiling!"
        )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="menu_main")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# Qidiruv
@router.callback_query(F.data == "menu_search")
async def cb_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(BotState.waiting_search)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="menu_main")]
    ])
    await callback.message.answer(
        "🔍 <b>Anime qidirish:</b>\n\nNomini yozib yuboring (Masalan: Solo Leveling, Demon Slayer, Naruto):",
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

# Tasodifiy Anime
@router.callback_query(F.data == "menu_random")
async def cb_random(callback: CallbackQuery):
    await callback.answer()
    animes = db.get("animes", [])
    if not animes:
        await callback.message.answer("Bazada anime mavjud emas.")
        return

    import random
    anime = random.choice(animes)
    text = (
        f"🎬 <b>{anime['title']}</b>\n\n"
        f"⭐ Reyting: <b>{anime['score']}/10</b>\n"
        f"📁 Janr: <i>{', '.join(anime['genres'])}</i>\n"
        f"🏢 Status: <b>{anime['status_uz']}</b>\n\n"
        f"{anime['description']}\n\n"
        f"👇 Tomosha qilish:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Qismlarni Ko'rish", callback_data=f"anime_{anime['id']}")],
        [
            InlineKeyboardButton(text="⭐ Sevimlilar", callback_data=f"fav_{anime['id']}"),
            InlineKeyboardButton(text="🎲 Boshqa anime", callback_data="menu_random")
        ],
        [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="menu_main")]
    ])
    if anime.get("poster_url"):
        await callback.message.answer_photo(anime["poster_url"], caption=text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# Sevimlilar (Watchlist)
@router.callback_query(F.data == "menu_watchlist")
async def cb_watchlist(callback: CallbackQuery):
    await callback.answer()
    user_id = str(callback.from_user.id)
    fav_ids = db.get("watchlists", {}).get(user_id, [])

    if not fav_ids:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Qidirish", callback_data="menu_search")],
            [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="menu_main")]
        ])
        await callback.message.edit_text("⭐ <b>Sevimli animelaringiz ro'yxati bo'sh.</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    kb_list = []
    text = "⭐ <b>Sizning Sevimli Animelaringiz:</b>\n\n"
    for idx, aid in enumerate(fav_ids, 1):
        a = next((x for x in db.get("animes", []) if x["id"] == aid), None)
        if a:
            text += f"{idx}. {a['title']}\n"
            kb_list.append([InlineKeyboardButton(text=f"🎬 {a['title'][:25]}", callback_data=f"anime_{a['id']}")])

    kb_list.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="menu_main")])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))

@router.callback_query(F.data.startswith("fav_"))
async def cb_toggle_fav(callback: CallbackQuery):
    aid = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    if "watchlists" not in db:
        db["watchlists"] = {}
    if user_id not in db["watchlists"]:
        db["watchlists"][user_id] = []

    if aid in db["watchlists"][user_id]:
        db["watchlists"][user_id].remove(aid)
        await callback.answer("Sevimlilardan olib tashlandi.")
    else:
        db["watchlists"][user_id].append(aid)
        await callback.answer("⭐ Sevimlilar ro'yxatiga qo'shildi!")
    save_db(db)

# Matn kiritilganda (Qidiruv)
@router.message(BotState.waiting_search)
async def process_search(message: Message, state: FSMContext):
    await state.clear()
    q = message.text.strip().lower()

    # Mahalliy bazadan
    local = [a for a in db.get("animes", []) if q in a["title"].lower()]
    if local:
        kb_list = [[InlineKeyboardButton(text=f"🎬 {a['title'][:28]}", callback_data=f"anime_{a['id']}")] for a in local[:6]]
        kb_list.append([InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="menu_main")])
        await message.answer(f"🔍 <b>\"{message.text}\"</b> bo'yicha topilgan animelar:", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))
        return

    # AniList dan
    ani = await search_anilist(q)
    if ani:
        kb_list = []
        for item in ani[:5]:
            t = item["title"].get("english") or item["title"].get("romaji")
            kb_list.append([InlineKeyboardButton(text=f"🎬 {t[:28]}", callback_data=f"ani_{item['id']}")])
        kb_list.append([InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="menu_main")])
        await message.answer(f"🔍 <b>\"{message.text}\"</b> bo'yicha natijalar:", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list))
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Qayta qidirish", callback_data="menu_search")],
        [InlineKeyboardButton(text="🏠 Asosiy Menyu", callback_data="menu_main")]
    ])
    await message.answer("❌ Hech qanday anime topilmadi.", reply_markup=kb)

# Epizodlarni ko'rish
@router.callback_query(F.data.startswith("anime_"))
async def cb_view_anime(callback: CallbackQuery):
    await callback.answer()
    aid = callback.data.split("_")[1]
    anime = next((x for x in db.get("animes", []) if x["id"] == aid), None)
    if not anime:
        await callback.message.answer("Anime topilmadi.")
        return

    kb_list = []
    for ep in anime.get("episodes", []):
        vip_tag = " 👑[VIP]" if ep.get("is_vip") else ""
        kb_list.append([InlineKeyboardButton(text=f"{ep['number']}-qism{vip_tag}", callback_data=f"ep_{anime['id']}_{ep['id']}")])

    kb_list.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_main")])
    await callback.message.answer(
        f"🎬 <b>{anime['title']}</b> — Qismlar ro'yxati (KageDub):",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_list)
    )

# Qismni ochish va VIP tekshiruvi
@router.callback_query(F.data.startswith("ep_"))
async def cb_watch_ep(callback: CallbackQuery):
    parts = callback.data.split("_")
    anime_id, ep_id = parts[1], parts[2]
    anime = next((x for x in db.get("animes", []) if x["id"] == anime_id), None)
    ep = next((e for e in anime.get("episodes", []) if e["id"] == ep_id), None) if anime else None

    if not ep:
        await callback.answer("Qism topilmadi.")
        return

    # VIP TEKSHIRUV: Agar qism VIP bo'lsa va foydalanuvchi VIP bo'lmasa
    user_is_vip = is_vip(callback.from_user.id)
    if ep.get("is_vip") and not user_is_vip:
        await callback.answer("👑 Bu qism faqat VIP obunachilar uchun! VIP olish uchun kanal adminiga murojaat qiling.", show_alert=True)
        return

    await callback.answer()
    text = (
        f"🎬 <b>{anime['title']} — {ep['number']}-qism</b>\n"
        f"🎙 Dublyaj: KageDub\n\n"
        f"👇 Quyidagi tugma orqali tomosha qiling:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Videoni Ochish", url=ep["url"])],
        [InlineKeyboardButton(text="🏠 Menyu", callback_data="menu_main")]
    ])
    await callback.message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# ==========================================
# 7. ADMIN PANEL (ADMIN VIP GA TEGMAYDI!)
# ==========================================
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    uid = message.from_user.id
    if uid != OWNER_ID and uid not in ADMIN_IDS:
        await message.answer("⛔ Sizda admin huquqlari mavjud emas!")
        return

    text = (
        "⚡ <b>KageDub Admin Paneli</b>\n\n"
        f"📢 Kanal: {CHANNEL_USERNAME}\n"
        f"🎬 Bazadagi animelar: {len(db.get('animes', []))} ta\n\n"
        "<i>Eslatma: VIP boshqaruvi faqat Owner (8318241400) uchun ochiq!</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga Post Yuborish", callback_data="admin_post_channel")],
        [InlineKeyboardButton(text="🏠 Menyu", callback_data="menu_main")]
    ])
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)

@router.callback_query(F.data == "admin_post_channel")
async def cb_admin_post(callback: CallbackQuery, bot: Bot):
    uid = callback.from_user.id
    if uid != OWNER_ID and uid not in ADMIN_IDS:
        return

    anime = db.get("animes", [])[0] if db.get("animes") else None
    if not anime:
        await callback.answer("Bazada anime yo'q!")
        return

    post_text = (
        f"🔥 <b>{anime['title']} — Yangi Qism Chiqdi!</b>\n\n"
        f"🎭 Janr: {', '.join(anime['genres'])}\n"
        f"🎙 Dublyaj: KageDub\n"
        f"⭐ Reyting: {anime['score']}/10\n\n"
        f"👇 <b>Botda tomosha qilish uchun bosing:</b>"
    )
    bot_info = await bot.get_me()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Botda Tomosha Qilish", url=f"https://t.me/{bot_info.username}?start=anime_{anime['id']}")]
    ])

    try:
        if anime.get("poster_url"):
            await bot.send_photo(chat_id=CHANNEL_ID, photo=anime["poster_url"], caption=post_text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=post_text, parse_mode=ParseMode.HTML, reply_markup=kb)
        await callback.answer("✅ Post @kagedub1 kanaliga yuborildi!", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)

# ==========================================
# 8. FAQAT OWNER (8318241400) UCHUN VIP BOSHQARUV
# ==========================================
@router.message(Command("owner"))
async def cmd_owner(message: Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ Bu bo'lim FAQAT bot egasi (Owner: 8318241400) uchun!")
        return

    vip_count = len(db.get("vip_users", {}))
    m_status = "🔴 Yoqilgan" if db.get("maintenance") else "🟢 O'chirilgan"
    text = (
        "👑 <b>Bosh Boshqaruvchi (Owner) Paneli</b>\n\n"
        f"🆔 Sizning ID: <b>8318241400</b>\n"
        f"👑 VIP Foydalanuvchilar: <b>{vip_count} ta</b>\n"
        f"🛠 Texnik ishlar: <b>{m_status}</b>\n\n"
        "<b>VIP Berish buyrug'i:</b>\n"
        "<code>/vip [ID] [KUN]</code>\n"
        "Masalan: <code>/vip 123456789 30</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢/🔴 Texnik Ishlar", callback_data="owner_toggle_maintenance")],
        [InlineKeyboardButton(text="👑 VIP Ro'yxatini Ko'rish", callback_data="owner_viplist")]
    ])
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=kb)

# /vip buyrug'i — FAQAT OWNER BOSHQARADI!
@router.message(Command("vip"))
async def cmd_vip(message: Message, bot: Bot):
    if message.from_user.id != OWNER_ID:
        await message.answer("⛔ <b>Ruxsat yo'q!</b> VIP boshqaruvi FAQAT Owner (8318241400) uchun. Adminlar VIP ga tegishi qat'iyan taqiqlangan.", parse_mode=ParseMode.HTML)
        return

    parts = message.text.split()
    if len(parts) >= 2:
        try:
            target_id = int(parts[1])
            days = int(parts[2]) if len(parts) >= 3 else 30
            exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

            if "vip_users" not in db:
                db["vip_users"] = {}

            db["vip_users"][str(target_id)] = {
                "user_id": target_id,
                "expires_at": "Cheksiz" if days == 9999 else exp_date,
                "is_active": True
            }
            save_db(db)

            await message.answer(f"✅ Foydalanuvchi <b>{target_id}</b> ga <b>{days} kunlik</b> VIP berildi!", parse_mode=ParseMode.HTML)
            try:
                await bot.send_message(chat_id=target_id, text=f"🎉 <b>Tabriklaymiz!</b> Sizga {days} kunlik KageDub VIP obunasi berildi!", parse_mode=ParseMode.HTML)
            except Exception:
                pass
            return
        except ValueError:
            await message.answer("Foydalanish: <code>/vip 123456789 30</code>", parse_mode=ParseMode.HTML)
            return

    # VIP a'zolar ro'yxati
    vips = db.get("vip_users", {}).values()
    text = "👑 <b>VIP A'zolar Ro'yxati:</b>\n\n"
    for idx, v in enumerate(vips, 1):
        text += f"{idx}. ID: <code>{v['user_id']}</code> | Tugash: {v['expires_at']}\n"
    text += "\nYangi VIP berish: <code>/vip [ID] [KUN]</code>"
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.callback_query(F.data == "owner_toggle_maintenance")
async def cb_owner_maint(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    db["maintenance"] = not db.get("maintenance", False)
    save_db(db)
    status = "🔴 Texnik ishlar yoqildi!" if db["maintenance"] else "🟢 Bot hamma uchun ochildi!"
    await callback.answer(status, show_alert=True)

@router.callback_query(F.data == "owner_viplist")
async def cb_owner_viplist(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return
    await callback.answer()
    vips = db.get("vip_users", {}).values()
    text = "👑 <b>VIP A'zolar Ro'yxati:</b>\n\n"
    for idx, v in enumerate(vips, 1):
        text += f"• ID: <code>{v['user_id']}</code> ({v['expires_at']})\n"
    await callback.message.answer(text, parse_mode=ParseMode.HTML)

# ==========================================
# 9. ISHGA TUSHIRISH (MAIN)
# ==========================================
async def main():
    print("⚡ [KageDub Bot - Python] Ishga tushirilmoqda...")
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    bot_info = await bot.get_me()
    print(f"🚀 Bot muvaffaqiyatli ishga tushdi: @{bot_info.username}")
    print(f"👑 Owner ID: {OWNER_ID} | 📢 Kanal: {CHANNEL_USERNAME}")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
