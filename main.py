import asyncio
import logging

import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command 
from aiogram.utils.keyboard import  ReplyKeyboardBuilder 
from aiogram import F

from utils import (create_table, get_quiz_index, 
                   get_question, quiz_data, update_quiz_index, get_rating,
                    get_last_question_index )


logging.basicConfig(level=logging.INFO)

API_TOKEN = '6895085715:AAEpVicvO1trADErO7ekAybG_pA76P6RCOI'
bot = Bot(token=API_TOKEN)
dp = Dispatcher()



# Загрузка данных квиза из JSON файла



#quiz_data = quiz_data_upload()





# Генерация клавиатуры с вариантами ответов


# Обработчик нажатия кнопки с правильным ответом


# Обработчик нажатия кнопки с неправильным ответом


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))


async def new_quiz(message):
    user_id = message.from_user.id
    last_question_index = await get_last_question_index(user_id)
    if last_question_index is None:
        current_question_index = 0
    else:
        current_question_index = last_question_index
    await update_quiz_index(user_id, current_question_index, 0)  # Начальный результат - 0
    await get_question(message, user_id)


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



async def main():
    await create_table()
    await start_bot()

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
