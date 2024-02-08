import asyncio
import logging
import json
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command 
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder 
from aiogram import F

logging.basicConfig(level=logging.INFO)

API_TOKEN = '6895085715:AAEpVicvO1trADErO7ekAybG_pA76P6RCOI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DB_NAME = r'F:\quiz_bot.db'

# Загрузка данных квиза из JSON файла
with open(r"C:\Users\пользователь\Desktop\quiz_questions.json", "r", encoding="utf-8") as file:
    quiz_data = json.load(file)





async def create_table():


    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (
                            user_id INTEGER PRIMARY KEY, 
                            question_index INTEGER,
                            last_question_index INTEGER,
                            score INTEGER)''')
        await db.commit()

# Генерация клавиатуры с вариантами ответов
def generate_options_keyboard(answer_options, right_answer_index):
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(answer_options):
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data=str(i) if i == right_answer_index else f"-{i}")  
        )
    builder.adjust(1)
    return builder.as_markup()

# Обработчик нажатия кнопки с правильным ответом
@dp.callback_query(F.data.regexp(r'^\d+$'))
async def process_answer(callback: types.CallbackQuery):
    current_question_index = await get_quiz_index(callback.from_user.id)
    selected_index = int(callback.data)
    selected_answer = quiz_data[current_question_index]['options'][selected_index]
    user_id = callback.from_user.id
    correct_index = quiz_data[current_question_index]['correct_option']
    correct_answer = quiz_data[current_question_index]['options'][correct_index]
    await callback.message.answer(f"Ваш ответ: {selected_answer}")
    if callback.message.reply_markup is not None:
        await callback.message.delete_reply_markup()
    if selected_index == correct_index:
        await callback.message.answer(f"Правильно!")
    else:
        await callback.message.answer(f"Неправильно. Правильный ответ: {correct_answer}")
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index, 1 if selected_index == correct_index else 0)
    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")

# Обработчик нажатия кнопки с неправильным ответом
@dp.callback_query(F.data.regexp(r'^-\d+$'))
async def process_wrong_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    current_question_index = await get_quiz_index(callback.from_user.id)
    selected_index = abs(int(callback.data))  
    selected_answer = quiz_data[current_question_index]['options'][selected_index]
    correct_index = quiz_data[current_question_index]['correct_option']
    correct_answer = quiz_data[current_question_index]['options'][correct_index]
    user_id = callback.from_user.id
    if selected_index == correct_index:
        await callback.message.answer(f"Ваш ответ: {selected_answer}. Правильно!")
    else:
        await callback.message.answer(f"Ваш ответ: {selected_answer}. Неправильно. Правильный ответ: {correct_answer}")
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index, 1 if selected_index == correct_index else 0)
    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

async def get_question(message, user_id):
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, correct_index)
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

async def new_quiz(message):
    user_id = message.from_user.id
    last_question_index = await get_last_question_index(user_id)
    if last_question_index is None:
        current_question_index = 0
    else:
        current_question_index = last_question_index
    await update_quiz_index(user_id, current_question_index, 0)  # Начальный результат - 0
    await get_question(message, user_id)

# Обработчик текстового сообщения "Начать игру"
@dp.message(F.text == "Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)

# Обработчик команды /rating
@dp.message(Command("rating"))
async def cmd_rating(message: types.Message):
    rating = await get_rating()
    if rating:
        rating_text = "\n".join([f"{idx + 1}. <b>{user_id}</b>: {score}" for idx, (user_id, score) in enumerate(rating)])
        await message.answer(f"<b>Рейтинг игроков:</b>\n{rating_text}", parse_mode="HTML")
    else:
        await message.answer("Рейтинг игроков пуст.")

async def get_rating():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, score FROM quiz_state ORDER BY score DESC') as cursor:
            return await cursor.fetchall()

async def get_quiz_index(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0

async def get_last_question_index(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT last_question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return None

async def update_quiz_index(user_id, index, score):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, last_question_index, score) VALUES (?, ?, ?, COALESCE((SELECT score FROM quiz_state WHERE user_id = ?), 0) + ?)', (user_id, index, index, user_id, score))
        await db.commit()

async def main():
    await create_table()
    await start_bot()

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
