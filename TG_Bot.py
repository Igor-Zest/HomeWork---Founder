# pip install aiogram
# pip install aiosqlite
## pip install nest_asyncio

# import nest_asyncio
# nest_asyncio.apply()

import asyncio
import logging # Модуль для ведения логов (для ошибок, событий и т.д.)
import aiosqlite # SQL Lite асинхронный интерфейс

import json


# Компоненты для работы с ботом
from aiogram import Bot, Dispatcher, types

from aiogram.filters.command import Command # Фильтр для обработки команд

from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder # Инструменты для создания встроенных и обычных клавиатур\кнопок.

from aiogram import F # Объект для работы с фильтрами.

# Включаем логирование
logging.basicConfig(level=logging.INFO)

API_TOKEN = '6895085715:AAEpVicvO1trADErO7ekAybG_pA76P6RCOI'

bot = Bot(token=API_TOKEN)

dp = Dispatcher()




DB_NAME = 'quiz_bot.db'

# Загрузка данных квиза из JSON файла
with open(r"C:\Users\пользователь\Desktop\quiz_questions.json", "r", encoding="utf-8") as file:
    quiz_data = json.load(file)


def generate_options_keyboard(answer_options, right_answer_index):
    builder = InlineKeyboardBuilder()

    for i, option in enumerate(answer_options):
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data=str(i) if i == right_answer_index else f"-{i}")  # Передаем индекс в callback_data
        )

    builder.adjust(1)
    return builder.as_markup()


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
    await update_quiz_index(callback.from_user.id, current_question_index)
    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")


@dp.callback_query(F.data.regexp(r'^-\d+$'))
async def process_wrong_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    current_question_index = await get_quiz_index(callback.from_user.id)
    selected_index = abs(int(callback.data))  # Получаем индекс выбранного неправильного ответа
    selected_answer = quiz_data[current_question_index]['options'][selected_index]
    correct_index = quiz_data[current_question_index]['correct_option']
    correct_answer = quiz_data[current_question_index]['options'][correct_index]
    user_id = callback.from_user.id
    # Если выбранный ответ совпадает с правильным, отправляем сообщение "Правильно!"
    if selected_index == correct_index:
        await callback.message.answer(f"Ваш ответ: {selected_answer}. Правильно!")
    else:
        await callback.message.answer(f"Ваш ответ: {selected_answer}. Неправильно. Правильный ответ: {correct_answer}")
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)
    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")


async def get_question(message, user_id):

    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, correct_index)
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


async def new_quiz(message):

    user_id = message.from_user.id
    current_question_index = 0

    await update_quiz_index(user_id, current_question_index)
    await get_question(message, user_id)


async def get_quiz_index(user_id):

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def update_quiz_index(user_id, index):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))

        await db.commit()


async def update_user_answer(user_id, question_index, user_answer, correct_answer):
    # Подключение к базе данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Обновление ответа пользователя в таблице user_answers
        await db.execute('INSERT OR REPLACE INTO user_answers (user_id, question_index, user_answer) VALUES (?, ?, ?)', (user_id, question_index, user_answer))
        
        # Здесь также обновляем таблицу quiz_results, чтобы сохранить рейтинг игрока
        # Предполагая, что вы хотите добавить 1 балл за каждый правильный ответ
        if user_answer == correct_answer:  
            await db.execute('INSERT OR REPLACE INTO quiz_results (user_id, score) VALUES (?, COALESCE((SELECT score FROM quiz_results WHERE user_id = ?), 0) + 1)', (user_id, user_id))
        
        await db.commit()


@dp.message(F.text == "Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):

    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)


async def create_table():

    async with aiosqlite.connect(DB_NAME) as db:

        # Создание таблицы quiz_state
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER)''')

        # Создание таблицы user_answers
        await db.execute('''CREATE TABLE IF NOT EXISTS user_answers (user_id INTEGER, question_index INTEGER, user_answer TEXT, PRIMARY KEY (user_id, question_index))''')
        
        # Создание таблицы quiz_results
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_results (user_id INTEGER PRIMARY KEY, score INTEGER)''')

        await db.commit()




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
        async with db.execute('SELECT user_id, score FROM quiz_results ORDER BY score DESC') as cursor:
            return await cursor.fetchall()



async def main():
    await create_table()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())