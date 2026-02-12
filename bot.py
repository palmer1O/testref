import asyncio
import aiosqlite
import urllib.parse
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.deep_linking import create_start_link

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "PASTE_NEW_TOKEN_HERE"
GROUP_LINK = "https://t.me/your_private_group_link"
ADMIN_ID = 5113023867

BASE_REWARD = 50
REF_REWARD = 30
MAX_REF = 5

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
                if referrer_id != user_id:
                    await add_referral(referrer_id)
                else:
                    referrer_id = None
            except:
                pass

        await add_user(user_id, referrer_id)

    link = await create_start_link(bot, str(user_id), encode=False)

    share_text = f"""🔥 Присоединяйся к StableDrop и получи до 200 USDT!

{link}"""

    share_url = "https://t.me/share/url?text=" + urllib.parse.quote(share_text)

    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Моя награда", callback_data="btn_stats")
    builder.button(text="🚀 Вступить в группу", url=GROUP_LINK)
    builder.button(text="💳 Указать USDT адрес", callback_data="btn_wallet")
    builder.button(text="📤 Поделиться ссылкой", url=share_url)
    builder.adjust(1)

    text = f"""
🔥 StableDrop

💰 Условия:
• 50 USDT за участие
• 30 USDT за каждого приглашённого (максимум 5)

📌 Чтобы получить дроп:
— Достаточно вступить в закрытую группу

📈 Приглашайте друзей, чтобы увеличить вашу награду

Ваша ссылка:
{link}
"""

    await message.answer(text, reply_markup=builder.as_markup())

# ================= МОЯ НАГРАДА =================
@dp.callback_query(F.data == "btn_stats")
async def callback_stats(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)

    if not user:
        await callback.message.answer("Сначала нажмите /start")
    else:
        referrals = min(user[2], MAX_REF)
        total_reward = BASE_REWARD + referrals * REF_REWARD

        await callback.message.answer(
            f"""💰 Ваша статистика

👥 Приглашено: {user[2]}
💵 Начислено: {total_reward} USDT"""
        )

    await callback.answer()

# ================= СОХРАНЕНИЕ КОШЕЛЬКА =================
@dp.callback_query(F.data == "btn_wallet")
async def callback_wallet(callback: CallbackQuery):
    await callback.message.answer("Введите ваш USDT адрес в сети TON:")
    await callback.answer()

@dp.message()
async def save_wallet_message(message: Message):
    if message.text.startswith("/"):
        return

    user = await get_user(message.from_user.id)
    if not user:
        return

    wallet = message.text.strip()
    if len(wallet) < 10:
        return

    await save_wallet(message.from_user.id, wallet)
    await message.answer("✅ Адрес сохранён. Ожидайте начисления.")

# ================= АДМИН ДОСТУП =================
@dp.message(Command("alluser"))
async def alluser(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Админ-доступ активирован.")

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
