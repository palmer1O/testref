import asyncio
import aiosqlite
import urllib.parse
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.deep_linking import create_start_link

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "7964951860:AAH65UxfUC0xrj9In4njb0jbEpUfk-KDn9g"
GROUP_ID = -1003609007517  # ваш приватный чат
ADMIN_ID = 5113023867

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            referrals INTEGER DEFAULT 0,
            joined INTEGER DEFAULT 0,
            wallet TEXT
        )
        """)
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_user(user_id, referrer_id=None):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, referrer_id) VALUES (?, ?)",
            (user_id, referrer_id)
        )
        await db.commit()

async def add_referral(referrer_id):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE users SET referrals = referrals + 1 WHERE user_id=?",
            (referrer_id,)
        )
        await db.commit()

async def set_joined(user_id):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE users SET joined=1 WHERE user_id=?",
            (user_id,)
        )
        await db.commit()

async def save_wallet(user_id, wallet):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE users SET wallet=? WHERE user_id=?",
            (wallet, user_id)
        )
        await db.commit()

# ================= START =================
@dp.message(Command("start"))
async def start(message: Message):
    args = message.text.split()
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        referrer_id = None
        if len(args) > 1:
            try:
                referrer_id = int(args[1])
                if referrer_id == user_id:
                    referrer_id = None
            except:
                pass
        await add_user(user_id, referrer_id)
        if referrer_id:
            await add_referral(referrer_id)

    # Персональная ссылка
    link = await create_start_link(bot, str(user_id), encode=False)

    # Ссылка для шаринга
    share_text = "🔥 Присоединяйся к StableDrop и получи до 200 $!"
    share_url = (
        "https://t.me/share/url?"
        f"url={urllib.parse.quote(link)}"
        f"&text={urllib.parse.quote(share_text)}"
    )

    # Создаём инвайт-ссылку в группу
    try:
        invite = await bot.create_chat_invite_link(chat_id=GROUP_ID, member_limit=1)
        group_url = invite.invite_link
    except:
        group_url = "https://t.me/joinchat/..."  # резервная ссылка

    # ================= Кнопки =================
    builder = InlineKeyboardBuilder()
    builder.button(text="Моя выплата", callback_data="btn_stats")
    builder.button(text="Вступить в группу", url=group_url)
    builder.button(text="💳 Указать адрес USDT ($)", callback_data="btn_wallet")
    builder.button(text="📤 Поделиться ссылкой", url=share_url)
    builder.adjust(1)

    text = f"""
🔥 StableDrop

📌 Чтобы получить дроп:
1. Вступите в закрытую группу

Приглашайте друзей, чтобы увеличить вашу выплату!

Ваша ссылка для приглашений:
{link}
"""
    await message.answer(text, reply_markup=builder.as_markup())

# ================= CALLBACKS =================
@dp.callback_query(F.data == "btn_stats")
async def callback_stats(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала нажмите /start")
    else:
        if user[3] == 0:
            await callback.message.answer("👥 Вы ещё не в группе. Текущая выплата: 0 $")
        else:
            referrals = user[2]
            payout = 50 + referrals * 30  # 50 за участие + 30 за каждого приглашённого
            await callback.message.answer(
                f"👥 Приглашено друзей: {referrals}\n💰 Текущая выплата: {payout} $"
            )
    await callback.answer()

@dp.callback_query(F.data == "btn_wallet")
async def callback_wallet(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Сначала нажмите /start")
    elif user[3] == 0:
        await callback.message.answer("Сначала вступите в группу, чтобы указать адрес USDT ($)")
    else:
        await callback.message.answer("Введите ваш адрес USDT в сети TON:")
    await callback.answer()

# ================= СОХРАНЕНИЕ АДРЕСА =================
@dp.message()
async def save_wallet_message(message: Message):
    if message.text.startswith("/"):
        return
    user = await get_user(message.from_user.id)
    if not user or user[3] == 0:
        return
    wallet = message.text.strip()
    if len(wallet) < 10:
        return
    await save_wallet(message.from_user.id, wallet)
    await message.answer("✅ Адрес сохранён. Ожидайте начисления.")

# ================= АДМИН-КОМАНДА =================
@dp.message(Command("alluser"))
async def alluser(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Админская команда выполнена")

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
