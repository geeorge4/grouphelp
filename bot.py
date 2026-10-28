import asyncio
import random
import os
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# ================= НАСТРОЙКИ =================
# Токен берется из переменных окружения (безопасно для GitHub)
BOT_TOKEN = os.getenv("BOT_TOKEN") 
# Твой ID (тоже можно вынести в переменные, но для теста оставим так)
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789")) 

# Включаем логирование
logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    print("ОШИБКА: Не найден BOT_TOKEN в переменных окружения!")
    exit(1)

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ================= ИГРА 21 (ОЧКО) =================
games_21 = {} # Храним состояние игры: {chat_id: {'player': id, 'cards': [], 'score': 0}}

def draw_card():
    # Упрощенная колода (2-11, где 11 это туз)
    return random.randint(2, 11)

@dp.message(Command("21"))
async def cmd_21(message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if chat_id in games_21:
        await message.answer("Игра уже идет! Напиши /стоп чтобы сбросить.")
        return

    # Начинаем игру
    card1 = draw_card()
    card2 = draw_card()
    games_21[chat_id] = {
        'player': user_id,
        'cards': [card1, card2],
        'score': card1 + card2
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🃏 Еще карту", callback_data="hit_21")],
        [InlineKeyboardButton(text="🛑 Хватит", callback_data="stand_21")]
    ])
    
    await message.answer(f"🎲 <b>Игра 21 началась!</b>\nТвои карты: {card1} и {card2}\nСумма: <b>{card1 + card2}</b>\n\nБудешь брать еще?", reply_markup=kb)

@dp.callback_query(F.data == "hit_21")
async def process_hit(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in games_21: return
    
    game = games_21[chat_id]
    if callback.from_user.id != game['player']:
        await callback.answer("Это не твоя игра!", show_alert=True)
        return

    new_card = draw_card()
    game['cards'].append(new_card)
    game['score'] += new_card
    
    if game['score'] > 21:
        # Перебор
        await callback.message.edit_text(f"💥 <b>Перебор!</b> Ты набрал {game['score']}. Ты проиграл.")
        del games_21[chat_id]
    elif game['score'] == 21:
        # Победа
        await callback.message.edit_text(f"🎉 <b>Очко!</b> У тебя ровно 21! Ты победил.")
        del games_21[chat_id]
    else:
        # Продолжаем
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🃏 Еще карту", callback_data="hit_21")],
            [InlineKeyboardButton(text="🛑 Хватит", callback_data="stand_21")]
        ])
        await callback.message.edit_text(f"Твои карты: {', '.join(map(str, game['cards']))}\nСумма: <b>{game['score']}</b>", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data == "stand_21")
async def process_stand(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    if chat_id not in games_21: return
    
    game = games_21[chat_id]
    if callback.from_user.id != game['player']:
        await callback.answer("Это не твоя игра!", show_alert=True)
        return

    score = game['score']
    if score <= 21:
        await callback.message.edit_text(f"🛑 Ты остановился на {score}. Неплохо!")
    del games_21[chat_id]
    await callback.answer()

@dp.message(Command("стоп"))
async def cmd_stop(message: Message):
    chat_id = message.chat.id
    if chat_id in games_21:
        del games_21[chat_id]
        await message.answer("Игра сброшена.")
    else:
        await message.answer("Активных игр нет.")

# ================= АДМИН-КОМАНДЫ (МУТ/КИК) =================
@dp.message(Command("мут"))
async def cmd_mute(message: Message):
    # Проверка на админа
    if message.from_user.id != ADMIN_ID and not message.from_user.is_chat_admin:
        await message.reply("У тебя нет прав для этой команды.")
        return
    
    if not message.reply_to_message:
        await message.reply("Ответь на сообщение пользователя, которого хочешь замутить.")
        return
    
    target = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=types.ChatPermissions(can_send_messages=False)
        )
        await message.reply(f"🔇 Пользователь {target.first_name} замучен.")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

@dp.message(Command("кик"))
async def cmd_kick(message: Message):
    if message.from_user.id != ADMIN_ID and not message.from_user.is_chat_admin:
        await message.reply("У тебя нет прав для этой команды.")
        return
    
    if not message.reply_to_message:
        await message.reply("Ответь на сообщение пользователя, которого хочешь кикнуть.")
        return
    
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=target.id)
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=target.id)
        await message.reply(f"👢 Пользователь {target.first_name} кикнут.")
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

# ================= СТАРТ =================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я — игровой бот. Вот что я умею:\n"
        "🎲 /21 — Сыграть в очко\n"
        "🔇 /мут (в ответ) — Замутить пользователя\n"
        "👢 /кик (в ответ) — Кикнуть пользователя\n"
    )

# ================= ЗАПУСК =================
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
