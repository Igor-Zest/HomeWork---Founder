import json
import aiosqlite
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

DB_NAME = r'F:\quiz_bot.db'



#def quiz_data_upload():
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

def generate_options_keyboard(answer_options, right_answer_index):
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(answer_options):
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data=str(i) if i == right_answer_index else f"-{i}")  
        )
    builder.adjust(1)
    return builder.as_markup()

async def get_quiz_index(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def get_question(message, user_id):
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, correct_index)
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)



async def get_rating():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT user_id, score FROM quiz_state ORDER BY score DESC') as cursor:
            return await cursor.fetchall()



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